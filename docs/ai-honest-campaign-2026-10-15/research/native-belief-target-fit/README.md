# Native-belief CX16 fit audit

The desktop native-belief prototypes are not directly ready for the current CX16
production bank layout. An isolated complete production link succeeds for the
baseline, but adding the unmodified core `AI_BELIEF_PRIORS` feature fails with:

```
Segment 'AIBSS' overflows memory area 'AI' by 1198 bytes
```

The baseline AI bank uses8147 of8192 bytes, leaving45 bytes. cc65 `-O -t cx16`
compilation measures the feature's contribution as820 additional AICODE bytes and
423 additional AIBSS bytes, totaling1243 bytes. The explicit two100-element uint16
prior arrays and owner byte account for401 BSS bytes; the compiler's static-local
allocation adds another22 bytes. Read-only data, ordinary BSS/data and zero page
are unchanged. Consequently the existing45-byte margin is exceeded by1198 bytes.
This is a measured link failure, not an estimate from desktop memory use.

Both attempts compile the actual complete production C/assembly source set with
BANKED_AI, all six normal production AI features, existing generated headers and
vendor library, original linker configuration and1024-byte C stack. Source trees
and all generated outputs are isolated in `/tmp`; every workspace/src file hash
was identical before and after. No core source, registered ID or frozen archive
changed. The added flag enables the core prior interface, without desktop
AI_TEST/AI_DIAGNOSTICS command features or a target posterior-computation driver.
Thus this already-minimal core variant exceeds the bank before any such additional
integration is considered.

`audit.json` retains exact commands, source/input hashes, object segments and link
diagnostics. Per-build logs and `target-build-evidence.zip` preserve generated
assembly/objects and the successful baseline map/symbols. Reproduce with
`tools/audit_native_belief_target_fit.py`. No optimization or proposed bank layout
change was implemented. Any target port needs a separately versioned design and
new target validation; desktop strength/mechanism results remain desktop evidence.
