import pandas as pd, numpy as np, sys
r = pd.read_csv(sys.argv[1]); mt = pd.read_csv(sys.argv[2])
print("scans", len(r), "| found", int(r.found.sum()))
print(r.groupby("expert_type").agg(scans=("found","size"), found=("found","sum")))
miss = r[~r.found]; print("MISSED:\n", miss[["patient","scan","expert_long","expert_vol","expert_lobe","expert_type","n_candidates","max_prob_in_tumour"]].to_string())
f = r[r.found].copy()
noise = 2.3
for v,(L,S,V,D,SP) in {"model":("tool_long","tool_short","tool_vol","dice","tool_spur_mm"),"halo":("halo_long","halo_short","halo_vol","halo_dice","halo_spur_mm"),"medsam2":("medsam2_long","medsam2_short","medsam2_vol","medsam2_dice","medsam2_spur_mm")}.items():
    le = f[L]-f.expert_long; se=f[S]-f.expert_short; ve=(f[V]-f.expert_vol)/f.expert_vol*100
    over = le>noise; tail = over & (f[SP]>2.0)
    print(f"{v:8s} n={len(f)} Dice med {f[D].median():.3f} | long err med {le.abs().median():.1f} mm (signed {le.median():+.1f}), within 2.3mm {np.mean(le.abs()<=noise)*100:.0f}% | short err med {se.abs().median():.1f} | vol err med {ve.abs().median():.0f}% (signed {ve.median():+.0f}%), within 17% {np.mean(ve.abs()<=17)*100:.0f}% | too long {over.sum()}, by tail {tail.sum()} | too short {(le<-noise).sum()}")
print("lobe agree", f"{(f.tool_lobe==f.expert_lobe).mean()*100:.0f}%", "type agree", f"{(f.tool_type==f.expert_type).mean()*100:.0f}%")
print("slice # within 2 of expert", f"{((f.tool_slice-f.expert_slice).abs()<=2).mean()*100:.0f}%")
print("candidates per scan: median", r.n_candidates.median(), "range", r.n_candidates.min(), r.n_candidates.max())
print("timing GPU nodules_s median", r.nodules_s.median(), "lobes_s", r.lobes_s.median(), "medsam2_s", f.medsam2_s.median())
m = mt.dropna(subset=["tumour_matched"])
print("pairs", len(mt), "| tumour pair evaluable", len(m), "matched", int(m.tumour_matched.sum()))
print("registration error med", mt.registration_error_mm.median(), "max", mt.registration_error_mm.max(), ">10mm:", (mt.registration_error_mm>10).sum())
print("candidates seen in both scans (retest side):", int(mt.n_pairs.sum()), "/", int(mt.n_current.sum()), f"= {mt.n_pairs.sum()/mt.n_current.sum()*100:.0f}%", "| test side", int(mt.n_pairs.sum()), "/", int(mt.n_prior.sum()))
