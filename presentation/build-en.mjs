import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const ROOT=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..');
const HOME=process.env.HOME;
const RUNTIME=process.env.CODEX_RUNTIME||`${HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies`;
process.env.RUNTIME_NODE_MODULES||=`${RUNTIME}/node/node_modules`;
process.env.RUNTIME_NODE||=process.execPath;
process.env.RUNTIME_PYTHON||=`${RUNTIME}/python/bin/python3`;
const SKILL=process.env.PRESENTATIONS_SKILL||`${HOME}/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/presentations`;
const {Presentation,PresentationFile}=await import(pathToFileURL(`${RUNTIME}/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs`).href);
const data=JSON.parse(await fs.readFile(`${ROOT}/presentation/data.json`,'utf8'));
const stamp=new Date().toISOString().replace(/[:.]/g,'-');
const WORK=`${HOME}/Downloads/CSLab_Presentation/english-${stamp}`;
await fs.mkdir(`${WORK}/build`,{recursive:true});await fs.mkdir(`${WORK}/output`,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});p.theme.defaultFont='Noto Sans';
const notes=[];const ink='#111111';
function text(sl,t,x,y,w,h,size=28,color=ink,bold=false,fill='none'){
 const box=sl.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});
 box.text=t;box.text.style={typeface:'Noto Sans',fontSize:size,color,bold};return box;
}
function slide(title,note,source='docs/methodology.md'){
 const s=p.slides.add();s.background.fill='#F4F2EE';const n=p.slides.items.length;
 text(s,'MEMORY TIERING / CSLab',55,24,1100,22,13,'#E1251B',true);
 text(s,title,55,70,1170,72,43,ink,true);
 text(s,'',0,685,1280,35,13,'#FFFFFF',false,'#111111');
 text(s,`Iason Zakynthinos / Advanced Computer Architecture                                      ${String(n).padStart(2,'0')} / 15`,55,690,1170,23,12,'#FFFFFF');
 s.speakerNotes.text=note+'\n\nSources: '+source;notes.push({title,note,source});return s;
}
async function image(s,file,x=55,y=150,w=1170,h=500){
 const b=await fs.readFile(`${ROOT}/${file}`);s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',alt:file,fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
function body(s,t,y=175,size=29,h=430){text(s,t,60,y,1140,h,size);}
function caption(s,t){text(s,t,60,646,1140,32,15,'#444444');}
let s=slide('How hot is a hot page?',
 '40 seconds. This course research project was carried out for Advanced Computer Architecture with CSLab. The target is M5 Figure 4, not a complete implementation of M5. Present the measurement method, discrepancies and controlled extensions.');
text(s,'M5 Figure 4',60,205,1130,100,78,ink,true);
body(s,'Custom pintool: accesses and modeled misses\n\nIason Zakynthinos\nCourse research project / NTUA',355,30,250);
s=slide('The assignment',
 '50 seconds. Record memory references, use the artifact benchmarks, reproduce the figure and extend it to accesses. Memstrata and NeoMem also informed the study. Figure 4 concerns spatial coverage, not the hot-page selection accuracy in Figure 3.');
body(s,'01    Record memory references with Intel Pin.\n\n02    Use benchmarks from the M5 artifact.\n\n03    Compare the figure for misses and accesses.',190,34);
s=slide('4 KiB = 64 lines x 64 B',
 '70 seconds. Count distinct lines for each page and window. The CDF at N is the fraction of observations touching at most N lines. Coverage is not access frequency. Each page-window observation has equal weight; epochs are not weighted equally regardless of population.');
body(s,'U(p,e): distinct lines in page p during window e.\n\nF(N): fraction of observations with 1 <= U <= N.\n\nN = 4, 8, 16, 32, 48.\n\nF(8)=0.40: 40% touched at most 8 lines, not 40% of accesses.',175,29);
s=slide('A custom pintool for the measurement',
 '70 seconds. Intel supplies the Pin framework. Our C++ implementation instruments memory operands, splits them into lines, filters them through caches and updates masks and counters. It does not retain a full trace. ROI hooks, shared epochs and manifests support validation and reproducibility.', 'src/profiler/pintool/hotskew.cpp; counter_table.hpp; paired_observer.hpp');
body(s,'memory operand -> 64 B lines -> cache filter -> masks / counters\n\nIntel Pin supplies the instrumentation framework.\n\nOur C++ code implements the measurement logic.\n\nOne execution, three streams. No large full trace.',185,29);
s=slide('Pin accesses vs device-side traffic',
 '70 seconds. A cache model is needed as a filter. It has private L1/L2, a shared LLC, writeback/write-allocate, LRU and non-inclusive behavior. It is not an exact Sapphire Rapids simulator. Pin sees virtual user-space operands, not kernel copies or hardware prefetches.');
body(s,'Private L1D/L2 and shared LLC.\nPrimary setting: 40 MiB / 10 ways.\n\nNo coherence, physical slice hashing or hardware prefetching.\n\nThese are modeled misses,\nnot hardware performance counters.',175,31);
s=slide('Shared windows, different streams',
 '70 seconds. Accesses are demand operands split by line. Fills are demand misses through every modeled cache level. Total traffic adds dirty LLC writebacks. All streams share boundaries in the same execution. The protocol uses 10M memory events, retains the final partial window and reports a separate whole-ROI union. Controls vary only declared factors.');
body(s,'Accesses             Demand line operands\n\nFills / misses       Demand misses through all cache levels\n\nTotal traffic         Fills + dirty LLC writebacks\n\nShared 10M-event windows. Whole ROI reported separately.',175,31);
s=slide('Common baseline: M5 / accesses / misses',
 '80 seconds. Top: digitized M5. Below: paired accesses and demand misses under a common protocol. This baseline precedes the new input campaign. It is not full replication. Retain it as the common basis for comparing controls.', 'docs/uniform-windows.md');
await image(s,'docs/assets/fig4_uniform_full.png');caption(s,'Baseline: kron-23; Google+ snapshot 1 for BC/SSSP; 1 thread/trial; digitized M5.');
s=slide('New inputs, unchanged measurement protocol',
 '70 seconds. The new campaign uses our declared Twitter reductions and Google+ snapshots 4/2. All six runs completed and passed checks. These are not the exact author inputs. Negative results are retained: BC and SSSP disagree more strongly.', 'docs/fidelity-followup.md');
await image(s,'docs/assets/fig4_fidelity_full.png');caption(s,'Twitter induced reductions; Google+ 4/2; exact M5 inputs and Figure 4 schedule remain unavailable.');
s=slide('Agreement did not improve everywhere',
 '50 seconds. Report the maximum absolute discrepancy across all five N thresholds, not just the tail. Do not substitute whole-ROI results because they look closer. The input campaign tests a hypothesis; it does not establish successful full reproduction.', 'results/fidelity-2026-10-27/scores.csv');
const names=['bfs','cc','pr','tc','bc','sssp'];
const values=[['Workload','Baseline / pp','New inputs / pp'],...names.map(n=>[n.toUpperCase(),...['baseline','real-input'].map(k=>data.scores.find(r=>r.kind===k&&r.workload===n).error_pp.toFixed(1))])];
const table=s.tables.add({rows:values.length,columns:3,left:60,top:165,width:1140,height:410,values,columnWidths:[380,380,380]});
table.borders.assign({fill:'#CCCCCC',width:1,style:'solid'});
for(let r=0;r<values.length;r++)for(let c=0;c<3;c++){const cell=table.getCell(r,c);cell.fill=r===0?'#111111':'#F4F2EE';cell.text.style={typeface:'Noto Sans',fontSize:26,bold:r===0,color:r===0?'#FFFFFF':'#111111'};}
caption(s,'Pooled demand-fill CDF. Lower means closer, not proof of an equivalent experiment.');
s=slide('Why do accesses and misses look alike?',
 '60 seconds. Touching a line sets one bit regardless of repeated hits. With cold initial caches, the first demand touch causes a fill, so whole-ROI line coverage can agree. This does not mean caches are ineffective. Baseline BFS has about 168.8M accesses and 7.9M fills.');
text(s,'168.8M accesses\n7.9M fills',60,185,1150,180,65,ink,true);
body(s,'Equal line coverage does not mean equal request counts.\n\nThe CDF measures distinct lines, not miss rate.',420,30,180);
s=slide('Declared controls and exploratory results',
 '60 seconds. Do not choose a separate protocol for each workload after inspecting M5. Stage 2 declares full-process collection, real inputs with twenty threads, nine LLC ways and RSS-selected TC. Select the footprint before looking at Pin CDFs. Closest cases are explicitly exploratory.', 'docs/pin-stage2-protocol.md');
if(data.stage2.completed>0){
 await image(s,'results/fidelity-stage2-2026-10-28/exploratory-closest-full.png');
 caption(s,'Reference-selected, not independent replication. Steps: '+data.stage2.completed+' / '+data.stage2.total+'. All outcomes retained.');
}else{
 const label=data.stage2.status.startsWith('waiting')?'waiting for repetition controls to complete':data.stage2.status;
 body(s,'Full process versus timed-kernel ROI.\nReal inputs with 20 software threads.\n9 LLC ways instead of 10.\nTC input selected using native RSS only.\n\nCompleted steps: '+data.stage2.completed+' / '+data.stage2.total+'\nStatus: '+label,170,28);
 const bfs=(data.repetition||[]).find(r=>r.workload==='bfs'&&r.scope==='pooled');
 if(bfs)caption(s,'BFS, 200 trials: pooled error '+bfs.error_pp.toFixed(1)+' pp versus 59.1. Repetition alone does not improve agreement.');
}
if(data.tc_footprint){
 const f=data.tc_footprint;
 let extra='TC native RSS: '+f.rss_gb.toFixed(2)+' GB; target '+f.target_gb.toFixed(1)+' GB. Within tolerance: '+f.within_tolerance+'. Selection used RSS only. This is not a size-matched reproduction.';
 if(f.pooled_fill_error_pp!==undefined)extra+=' The completed one-thread control has pooled miss error '+f.pooled_fill_error_pp.toFixed(2)+' pp, worse than 34.87 pp for the smaller input. The twenty-thread control is a separate experiment.';
 notes[10].note+='\n\n'+extra;s.speakerNotes.text+='\n\n'+extra;
}
s=slide('The same comparison in SimCXL',
 '70 seconds. The probe measures physical accepted requests at the CXL bridge. Bridge and controller clocks are independent; never add their observations together. The overview compares different setups, not identical traces. All six graph workloads completed and passed checks. TC: 621,867,320 requests in 63 windows, 31.07 hours, maximum discrepancy 37.78 percentage points. PR is numerically close, but full reproduction is not established. Liblinear and BC window controls remain in the simulator queue.', 'docs/simulator-figure4.md');
await image(s,'results/revalidated-2026-10-25/sim-comparison/figure4-m5-pin-simulator.png');
caption(s,'PR: '+(data.simulator.pr||'queued')+' · TC: '+(data.simulator.tc||'queued')+' · Snapshot resume: bounded validation passed, reboot untested.');
s=slide('PAC / WAC and bounded trackers',
 '60 seconds. Exact page/word counts provide ground truth. HPT/HWT are bounded trackers using Space-Saving and Count-Min plus top-K. Corrected runs completed. This is not the complete M5 hardware or tiering manager. Tracker N is a capacity budget, distinct from N in the CDF thresholds.', 'docs/revalidation-2026-10-25.md');
await image(s,'results/revalidated-2026-10-25/figures/trackers.png',55,150,790,470);
text(s,'Exact counters:\nPAC / WAC\n\nBounded trackers:\nHPT / HWT\n\nSpace-Saving\nCount-Min + top-K',870,190,345,420,25);
s=slide('Beyond the original figure',
 '50 seconds. Validated extensions cover granularity, turnover and previous-window placement. A coarser tracking unit changes apparent density, not the physical cache-line size. Redis A/C, Memcached and Liblinear are included in the broader study. The serial latency cost model is not measured application speedup.', 'docs/revalidation-2026-10-25.md');
await image(s,'results/revalidated-2026-10-25/figures/granularity.png',55,150,790,470);
text(s,'Granularity sweeps\n\nHot-set turnover\n\nPrevious-window placement\n\nSerial cost sensitivity\nnot measured\napplication speedup',870,190,345,420,25);
s=slide('What exact reproduction still requires',
 '50 seconds. Correct implementation of our counters does not recover the exact reference procedure. We still need the reduced graphs, WAC collection schedule and page population. Controls continue, but the objective is to explain discrepancies without selecting attractive bars after the fact.', 'docs/m5-parameter-evidence.md');
body(s,'Exact reduced graphs, weights and vertex ordering.\n\nWAC resets, region collection and aggregation.\n\nComparable scope and page population.\n\nRetain improvements alongside negative results\nand unresolved limitations.',175,30);
for(const [i,sl] of p.slides.items.entries()){
 const blob=await p.export({slide:sl,format:'png',scale:1});
 await fs.writeFile(`${WORK}/build/slide-${i+1}.png`,new Uint8Array(await blob.arrayBuffer()));
 console.log('Rendered',i+1);
}
await fs.writeFile(`${WORK}/output/speaker-notes-en.md`,notes.map((n,i)=>`## ${i+1}. ${n.title}\n\n${n.note}\n\nSources: ${n.source}\n`).join('\n'));
const candidate=`${WORK}/build/draft.pptx`;await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(`${SKILL}/container_tools/artifact_tool_utils.mjs`).href);
const final=`${WORK}/output/CSLab_Memory_Tiering_English.pptx`;
console.log(await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:final,
 pythonExecutable:`${RUNTIME}/python/bin/python3`,
 integrityValidatorPath:`${SKILL}/container_tools/inspect_presentation_package_integrity.py`,
 layoutValidatorPath:`${SKILL}/container_tools/inspect_presentation_layout_geometry.py`,
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:['Noto Sans']},verifyArtifactToolImport:true,receiptPath:`${WORK}/build/validation.json`}));
await fs.writeFile(`${ROOT}/presentation/latest-en.json`,JSON.stringify({path:final,work:WORK,data:`${ROOT}/presentation/data.json`},null,2)+'\n');
console.log(final);
