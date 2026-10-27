// Deterministic induced subgraphs of the official Twitter release. Selection
// depends only on vertex IDs, never on an observed M5 score. GAPBS builds CSR.
#include <zlib.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

class Input {
    gzFile file_=nullptr;
    std::string directory_;
    int part_=0;
    std::array<unsigned char, 1<<20> buffer_{};
    int at_=0, size_=0;
    void open_part() {
        std::string name=directory_+"/twitter_rv.net.0"+std::to_string(part_)+".gz";
        file_=gzopen(name.c_str(),"rb");
        if (!file_) throw std::runtime_error("cannot open "+name);
    }
public:
    explicit Input(const std::string& directory):directory_(directory){open_part();}
    ~Input(){if(file_)gzclose(file_);}
    int byte() {
        while(at_==size_){
            if(!file_)return -1;
            size_=gzread(file_,buffer_.data(),buffer_.size());at_=0;
            if(size_<0)throw std::runtime_error("gzip read failed");
            if(!size_){
                gzclose(file_);file_=nullptr;
                if(++part_>=4)return -1;
                open_part();
            }
        }
        return buffer_[at_++];
    }
    bool number(uint32_t& value) {
        int c; do {c=byte();} while(c>=0 && c<=32);
        if(c<0)return false;
        uint64_t n=0;
        do {
            if(c<'0'||c>'9')throw std::runtime_error("non-integer input");
            n=n*10+static_cast<unsigned>(c-'0');
            if(n>=(1u<<27))throw std::runtime_error("unexpected vertex ID");
            c=byte();
        } while(c>32);
        value=static_cast<uint32_t>(n);return true;
    }
};

uint64_t mix(uint64_t x) {
    x+=0x9e3779b97f4a7c15ULL;
    x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL;
    return x^(x>>31);
}

int main(int argc,char** argv) try {
    if(argc!=4 && argc!=6)throw std::runtime_error("usage: prepare_twitter SOURCE_DIR MAIN.el TC.el [EXPECTED_NODES EXPECTED_EDGES]");
    uint64_t expected_nodes=argc==6?std::stoull(argv[4]):41652230;
    uint64_t expected_edges=argc==6?std::stoull(argv[5]):1468365182ULL;
    constexpr uint32_t limit=1u<<27, missing=UINT32_MAX;
    std::vector<uint8_t> seen(limit/8,0);
    uint32_t max_id=0;
    uint64_t edges=0;
    auto scan=[&](auto consume) {
        Input input(argv[1]); uint32_t u,v;
        while(input.number(u)) {
            if(!input.number(v))throw std::runtime_error("incomplete edge");
            consume(u,v);
        }
    };
    scan([&](uint32_t u,uint32_t v){seen[u/8]|=1u<<(u%8);seen[v/8]|=1u<<(v%8);
        max_id=std::max(max_id,std::max(u,v));++edges;});
    std::vector<uint32_t> main_map(max_id+1,missing),tc_map(max_id+1,missing);
    uint32_t nodes=0,main_nodes=0,tc_nodes=0;
    for(uint32_t u=0;u<=max_id;++u) if(seen[u/8]&(1u<<(u%8))) {
        ++nodes;uint32_t bucket=mix(u)%4;
        if(bucket<3)main_map[u]=main_nodes++;
        if(bucket<1)tc_map[u]=tc_nodes++;
    }
    if(nodes!=expected_nodes || edges!=expected_edges)
        throw std::runtime_error("published Twitter node/edge totals do not match");
    FILE* main_out=std::fopen(argv[2],"wx");
    FILE* tc_out=std::fopen(argv[3],"wx");
    if(!main_out||!tc_out)throw std::runtime_error("output exists or cannot be created");
    std::setvbuf(main_out,nullptr,_IOFBF,1<<20);std::setvbuf(tc_out,nullptr,_IOFBF,1<<20);
    uint64_t main_edges=0,tc_edges=0;
    scan([&](uint32_t u,uint32_t v){
        if(main_map[u]!=missing&&main_map[v]!=missing) {
            if(std::fprintf(main_out,"%u %u\n",main_map[u],main_map[v])<0)throw std::runtime_error("write failed");
            ++main_edges;
        }
        if(tc_map[u]!=missing&&tc_map[v]!=missing) {
            if(std::fprintf(tc_out,"%u %u\n",tc_map[u],tc_map[v])<0)throw std::runtime_error("write failed");
            ++tc_edges;
        }
    });
    // GAPBS infers vertex count before dropping self-loops. Preserve selected
    // trailing isolated vertices without adding an edge to the final CSR.
    if(main_nodes && std::fprintf(main_out,"%u %u\n",main_nodes-1,main_nodes-1)<0)throw std::runtime_error("write failed");
    if(tc_nodes && std::fprintf(tc_out,"%u %u\n",tc_nodes-1,tc_nodes-1)<0)throw std::runtime_error("write failed");
    if(std::fclose(main_out)||std::fclose(tc_out))throw std::runtime_error("close failed");
    std::cout<<"{\"source_nodes\":"<<nodes<<",\"source_edges\":"<<edges
             <<",\"main_nodes\":"<<main_nodes<<",\"main_edges\":"<<main_edges
             <<",\"tc_nodes\":"<<tc_nodes<<",\"tc_edges\":"<<tc_edges
             <<",\"vertex_count_self_loop_sentinel\":true}\n";
    return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
