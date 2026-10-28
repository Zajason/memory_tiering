## 1. Πόσο θερμή είναι μια θερμή σελίδα;

40 δευτερόλεπτα. Η ερευνητική εργασία έγινε στο μάθημα Προηγμένη Αρχιτεκτονική Υπολογιστών με το CSLab. Κύριο ζητούμενο είναι το Figure 4 του M5, όχι πλήρης υλοποίηση του συστήματος. Θα παρουσιάσω τη μέτρηση, την απόκλιση και τις ελεγχόμενες επεκτάσεις.

Πηγές: docs/methodology.md

## 2. Η ανάθεση

50 δευτερόλεπτα. Καταγραφή memory references, χρήση artifact benchmarks, αναπαραγωγή του γραφήματος και επέκταση για accesses. Memstrata και NeoMem αποτέλεσαν επίσης το πλαίσιο μελέτης. Το γράφημα αφορά χωρική κάλυψη, όχι ακρίβεια hot-page selection του Figure 3.

Πηγές: docs/methodology.md

## 3. 4 KiB = 64 γραμμές × 64 B

70 δευτερόλεπτα. Για κάθε σελίδα και παράθυρο κρατάμε διαφορετικές γραμμές. Η CDF στο N δείχνει το ποσοστό των παρατηρήσεων με έως N γραμμές. Η κάλυψη δεν μετρά συχνότητα. Κάθε page-window έχει ίσο βάρος, όχι κάθε epoch ανεξάρτητα από το μέγεθός του.

Πηγές: docs/methodology.md

## 4. Το pintool γράφτηκε για τη μέτρηση.

70 δευτερόλεπτα. Η Intel παρέχει το framework Pin. Η δική μας C++ υλοποίηση κάνει instrumentation των memory operands, διαχωρισμό σε γραμμές, cache filtering και bitmasks/counters. Δεν αποθηκεύει πλήρες trace. ROI hooks, κοινά epochs και manifests επιτρέπουν έλεγχο και επανάληψη.

Πηγές: src/profiler/pintool/hotskew.cpp; counter_table.hpp; paired_observer.hpp

## 5. Το Pin βλέπει accesses. Το M5 βλέπει μνήμη.

70 δευτερόλεπτα. Χρειάζεται μοντέλο cache ως φίλτρο. Το μοντέλο έχει private L1/L2, shared LLC, writeback/write-allocate, LRU και non-inclusive συμπεριφορά. Δεν είναι ακριβής Sapphire Rapids simulator. Οι αιτήσεις είναι virtual user-space operands. Δεν παρατηρούνται kernel copies ή hardware prefetches.

Πηγές: docs/methodology.md

## 6. Κοινό παράθυρο, διαφορετικές ροές.

70 δευτερόλεπτα. Accesses είναι τα demand operands ανά γραμμή. Fills είναι demand misses σε όλα τα επίπεδα. Traffic προσθέτει dirty LLC writebacks. Τα όρια είναι κοινά στην ίδια εκτέλεση. Το αρχικό πρωτόκολλο έχει 10M memory events, final partial window και χωριστή whole-ROI union. Η νέα καμπάνια αλλάζει μόνο δηλωμένους παράγοντες.

Πηγές: docs/methodology.md

## 7. Η κοινή βάση: M5 / accesses / misses

80 δευτερόλεπτα. Πάνω ψηφιοποιημένο M5. Κάτω οι paired προσπελάσεις και demand misses με κοινό πρωτόκολλο. Η εικόνα είναι η baseline πριν από τη νέα οικογένεια inputs. Δεν πρέπει να συγχέεται με πλήρη replication. Κρατάμε αυτή τη βάση για σύγκριση των controls.

Πηγές: docs/uniform-windows.md

## 8. Νέα inputs — ίδιο πρωτόκολλο μέτρησης

70 δευτερόλεπτα. Η νέα καμπάνια χρησιμοποιεί δικές μας προδηλωμένες Twitter reductions και Google+ snapshots 4/2. Όλες οι έξι εκτελέσεις έχουν ολοκληρωθεί και περάσει τους ελέγχους. Τα inputs δεν είναι τα ακριβή των συγγραφέων. Δείχνουμε και αρνητικά αποτελέσματα: μεγαλύτερη απόκλιση για BC και SSSP.

Πηγές: docs/fidelity-followup.md

## 9. Η συμφωνία δεν βελτιώθηκε παντού.

50 δευτερόλεπτα. Μέγιστη απόλυτη διαφορά στα πέντε N. Δεν επιλέγουμε μόνο την ουρά. Τα pooled αποτελέσματα δεν αντικαθίστανται από whole-ROI επειδή εκεί η συμφωνία είναι καλύτερη. Η νέα καμπάνια είναι ουσιαστικός έλεγχος υπόθεσης, όχι επιτυχής πλήρης αναπαραγωγή.

Πηγές: results/fidelity-2026-10-27/scores.csv

## 10. Γιατί accesses και misses μοιάζουν;

60 δευτερόλεπτα. Η ίδια γραμμή προσθέτει ένα bit, ανεξαρτήτως hits. Σε κρύες caches το πρώτο demand touch κάνει fill, οπότε whole-ROI coverage ταιριάζει. Αυτό δεν λέει ότι η cache δεν βοηθά. Το baseline BFS έχει περίπου 168.8M accesses και 7.9M fills.

Πηγές: docs/methodology.md

## 11. Τι δοκιμάζεται τώρα;

60 δευτερόλεπτα. Δεν επιλέγουμε πρωτόκολλο ανά workload αφού δούμε τη reference. Η δεύτερη καμπάνια είναι προδηλωμένη: full-process collection, πραγματικά inputs με είκοσι threads, εννέα ways και RSS-selected TC. Το footprint επιλέγεται πριν από τα Pin CDFs. Τα καλύτερα cases επισημαίνονται ως exploratory.

Πηγές: docs/pin-stage2-protocol.md

## 12. Το ίδιο γράφημα στο SimCXL

70 δευτερόλεπτα. Η probe μετρά physical accepted requests στο CXL bridge. Τα bridge/controller clocks είναι ανεξάρτητα και δεν αθροίζονται. Το overview συγκρίνει διαφορετικά setups και όχι identical traces. Οι μη ολοκληρωμένες εκτελέσεις είναι pending, όχι μηδενικές μπάρες.

Πηγές: docs/simulator-figure4.md

## 13. PAC / WAC και bounded trackers

60 δευτερόλεπτα. Exact page/word counts παρέχουν ground truth. HPT/HWT είναι περιορισμένοι trackers, με Space-Saving και Count-Min + top-K. Οι corrected runs ολοκληρώθηκαν. Δεν παρουσιάζουμε πλήρες M5 hardware ή tiering manager. Το N του tracker είναι budget και διαφέρει από το N κατώφλι των CDF bars.

Πηγές: docs/revalidation-2026-10-25.md

## 14. Πέρα από το αρχικό γράφημα

50 δευτερόλεπτα. Validated granularity, turnover και previous-window placement. Η coarser μονάδα tracking αλλάζει apparent density, όχι φυσικά το cache-line size. Υπάρχουν Redis A/C, Memcached, Liblinear. Το serial latency cost model δεν είναι μετρημένο speedup.

Πηγές: docs/revalidation-2026-10-25.md

## 15. Τι χρειάζεται για πραγματική αναπαραγωγή;

50 δευτερόλεπτα. Η υλοποίηση και η ορθότητα των δικών μας μετρητών δεν δίνουν την exact reference διαδικασία. Χρειάζονται reduced graphs, WAC collection schedule και page population. Οι έλεγχοι συνεχίζονται, αλλά ο στόχος είναι να εξηγήσουμε τη διαφορά χωρίς post-hoc επιλογή ωραίων bars.

Πηγές: docs/m5-parameter-evidence.md
