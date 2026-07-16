# Prediction models

The large LSTM weight files (`model.pt`, `fine_tuned_model.pt`, ~39 MB each) are
**not** committed to git or shipped inside the pip package. They are hosted as
release assets and downloaded on first use. The small files needed for every run -
the tokenizer (`spm_pl.model`) and the fallback unigram list (`unigrams200k.csv`) -
are bundled in the package.

## How a model file is located

When the app needs a model file it looks, in order:

1. **`AAC_MODELS_DIR`** environment variable, if it points at a directory holding the
   file — use this to pin a specific local copy.
2. The **bundled** `models/` directory (present in a source checkout and for the
   small bundled files).
3. The **per-user cache**: `~/.cache/aac_app/models/` (honours `XDG_CACHE_HOME`).
4. **Download** from the manifest into the cache, verifying its SHA-256.

The first hit wins. So on a developer machine the bundled files are used; on an
installed machine the weights are downloaded once and then read from the cache.

## Downloading ahead of time

To prepare a machine before running the experiment offline:

```bash
start_app --download-models
```

This fetches every model in the manifest into the cache and exits. Alternatively,
copy the `.pt` files into `~/.cache/aac_app/models/` by hand, or point
`AAC_MODELS_DIR` at a directory that contains them.

## Choosing which model to use

```bash
start_app --model fine_tuned_model.pt
```

If the chosen model is not available locally it is downloaded first (provided its
URL is in the manifest).
