# bpcs_adaptive

Labtainer package for bpcs_adaptive.

## Install

```bash
imodule https://github.com/minhtamcoc/BPCS_Adaptive/raw/main/bpcs_adaptive.tar.gz
labtainer bpcs_adaptive
```

## Docker image

```text
tammaycay/bpcs_adaptive.bpcs_adaptive.student:latest
```

## Checkwork performance note

This release includes `config/skip_starts.txt` so generated frame folders, extracted media, and stego videos are not packed into the Labtainer result archive. The grading checks still use the small report/JSON/text files required by `results.config`.
