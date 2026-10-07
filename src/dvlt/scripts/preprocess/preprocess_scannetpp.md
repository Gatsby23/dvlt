# ScanNet++ preprocessing (training + evaluation)

[ScanNet++](https://kaldir.vc.in.tum.de/scannetpp/) DSLR captures, rectified to a
pinhole model with per-frame metric depth rendered from the aligned GT mesh.
Train split `nvs_sem_train`, eval split `nvs_sem_val`.

## 1. Download

Register at <https://kaldir.vc.in.tum.de/scannetpp/>, accept the license, and use
the official downloader to fetch the DSLR data and meshes. Expected raw layout
(`--data_root`):

```text
scannetpp_raw/
├── splits/
│   ├── nvs_sem_train.txt
│   └── nvs_sem_val.txt
├── metadata/semantic_classes.txt           # semantic ID ordering (read)
└── data/
    └── <SCENE_ID>/
        ├── scans/mesh_aligned_0.05.ply         # GT mesh (read)
        ├── scans/mesh_aligned_0.05_semantic.ply  # vertex semantics (read)
        └── dslr/
            ├── resized_images/*.JPG           # fisheye RGB (read)
            ├── colmap/images.txt              # poses (read)
            └── nerfstudio/transforms.json     # intrinsics + distortion (read)
```

## 2. Install (preprocess-only)

Depth rendering needs PyTorch3D. It compiles against the `torch` already in your
env, so build with `--no-build-isolation` and install a matching CUDA toolchain
first (torch 2.5.1 → CUDA 12.4):

```bash
conda install -c "nvidia/label/cuda-12-4" cuda-toolkit
pip install plyfile ninja fvcore iopath
FORCE_CUDA=1 pip install "git+https://github.com/facebookresearch/pytorch3d.git@stable" --no-build-isolation
```

`open3d` and `opencv-python` come with the core install. `cuda-toolkit` provides
the `nvcc` the build needs; `FORCE_CUDA=1` compiles the CUDA kernels even on a node
without a visible GPU. `plyfile` reads the vertex labels in
`mesh_aligned_0.05_semantic.ply`.

## 3. Run

One command processes both splits end to end (discovers scenes from the split
files, renders depth and wall/floor/ceiling labels, undistorts, and writes the
result in the layout the configs expect):

```bash
python -m dvlt.scripts.preprocess.scannetpp.preprocess \
    --data_root datasets/scannetpp_raw \
    --output_root datasets
```

- `--data_root`: the raw release (step 1).
- `--output_root`: same as the `user.data_root`

Options: `--splits nvs_sem_val` (eval only), `--scene_ids <id> ...` (subset),
`--device` (default `cuda`). Structural masks are always generated and require
`scans/mesh_aligned_0.05_semantic.ply` and `metadata/semantic_classes.txt`.
Each invocation reprocesses the selected scenes and replaces their existing outputs.

### Rasterization speed (optional)

`--bin_size` controls the rasterizer's pixel-bin size;
`--max_faces_per_bin` caps the number of candidate mesh faces per bin. These
settings control speed and memory, not the spatial resolution of the mask.
Too small a face cap can leave faces out of the result. For quality-first
preprocessing, omit both options and inspect the rendered depth and structural
masks before tuning. The following is only a performance experiment; compare
its output with the default on representative scenes before using it at scale:

```bash
python -m dvlt.scripts.preprocess.scannetpp.preprocess \
    --data_root datasets/scannetpp_raw \
    --output_root datasets \
    --bin_size 128 --max_faces_per_bin 200000
```

## 4. Output

With `--output_root datasets`:

```text
datasets/
├── train/scannetpp/
│   ├── nvs_sem_train.txt
│   └── scannetpp_undistort/<SCENE_ID>/
│       ├── undistorted_images/*.JPG
│       ├── undistorted_depth/*.png                 # 16-bit metric depth
│       ├── struct_mask/*.png                          # uint8: 0 other/unlabeled, 1 wall, 2 floor, 3 ceiling
│       └── nerfstudio/transforms_undistorted.json  # PINHOLE intrinsics
└── test/scannetpp/
    ├── nvs_sem_val.txt
    └── scannetpp_undistort/<SCENE_ID>/...
```

Then set the configs' `user.data_root` to `--output_root` (here `datasets/`).
`nvs_sem_train` lands under `train/`, `nvs_sem_val` under `test/`, matching
[`train_datasets/scannetpp.yaml`](../../config/experiments/data/train_datasets/scannetpp.yaml)
and
[`test_datasets/scannetpp.yaml`](../../config/experiments/data/test_datasets/scannetpp.yaml).

## Notes

- Depth is rasterized through the original fisheye camera from the GT mesh, then
  rectified to pinhole with nearest-neighbour resampling (matching the images'
  rectification).
- The structural mask uses majority voting over the three vertex labels of each
  visible mesh face, then the same nearest-neighbour rectification as depth.
  It contains only wall, floor, and ceiling. These PNGs are saved for downstream
  use; the current ScanNet++ dataset loader does not yet expose them to training.
- Depth PNGs store the float16 bit-pattern read by
  [`common.io.read_depth`](../../common/io.py); read them back with that function.

To inspect the wall/floor/ceiling masks alongside the rectified RGB images, run
`python scripts/visualize_scannetpp_structure.py --scene-dir <processed-scene-dir> --frame <image-stem>`
from the repository root. The comparison image is saved in the scene's
`struct_visualizations/` directory. Its legend uses 0 for other/unlabeled/no mesh,
1 for wall, 2 for floor, and 3 for ceiling.
