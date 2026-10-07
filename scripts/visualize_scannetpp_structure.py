"""Compare ScanNet++ rectified RGB images with their structural segmentation masks.

Example:
    python scripts/visualize_scannetpp_structure.py \
        --scene-dir /path/to/processed/test/scannetpp/scannetpp_undistort/SCENE_ID \
        --frame DSC03468
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


CLASS_NAMES = ("Other / unlabeled / no mesh", "Wall", "Floor", "Ceiling")
CLASS_COLORS = np.array([(35, 35, 35), (235, 65, 65), (70, 190, 100), (70, 125, 245)], dtype=np.uint8)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def get_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def make_comparison(rgb_path: Path, mask_path: Path, alpha: float) -> Image.Image:
    with Image.open(rgb_path) as src:
        rgb = np.asarray(src.convert("RGB"))
    with Image.open(mask_path) as src:
        mask = np.asarray(src)

    if mask.ndim != 2 or not np.issubdtype(mask.dtype, np.integer):
        raise ValueError(f"Expected a single-channel integer mask: {mask_path}")
    if mask.shape != rgb.shape[:2]:
        raise ValueError(f"RGB and mask sizes differ: {rgb_path} {rgb.shape[:2]}, {mask_path} {mask.shape}")
    values = np.unique(mask)
    if np.any(values > 3) or np.any(values < 0):
        raise ValueError(f"Unexpected mask values {values.tolist()} in {mask_path}; expected 0, 1, 2, 3")

    colored = CLASS_COLORS[mask]
    overlay = rgb.copy()
    structural = mask > 0
    overlay[structural] = (
        (1 - alpha) * rgb[structural].astype(np.float32) + alpha * colored[structural].astype(np.float32)
    ).astype(np.uint8)

    height, width = mask.shape
    gap, top, bottom = 16, 58, 82
    canvas = Image.new("RGB", (3 * width + 4 * gap, height + top + bottom), "white")
    draw = ImageDraw.Draw(canvas)
    font = get_font(24)
    small_font = get_font(18)
    panels = (Image.fromarray(rgb), Image.fromarray(overlay), Image.fromarray(colored))
    for index, (title, panel) in enumerate(zip(("RGB", "Overlay", "Structure labels"), panels, strict=True)):
        x = gap + index * (width + gap)
        draw.text((x, 14), title, fill="black", font=font)
        canvas.paste(panel, (x, top))

    counts = np.bincount(mask.ravel(), minlength=4)
    y = top + height + 18
    for value, (name, color, count) in enumerate(zip(CLASS_NAMES, CLASS_COLORS, counts, strict=True)):
        x = gap + value * (width * 3 // 4 + gap)
        draw.rectangle((x, y, x + 24, y + 24), fill=tuple(int(c) for c in color))
        percent = count * 100.0 / mask.size
        draw.text((x + 33, y), f"{value}: {name} ({percent:.1f}%)", fill="black", font=small_font)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize ScanNet++ wall/floor/ceiling segmentation")
    parser.add_argument("--scene-dir", type=Path, required=True, help="Processed scene directory")
    parser.add_argument("--frame", help="One image filename or stem, e.g. DSC03468.JPG or DSC03468")
    parser.add_argument("--limit", type=int, default=5, help="Maximum frames without --frame; 0 means all (default: 5)")
    parser.add_argument("--output-dir", type=Path, help="Defaults to SCENE_DIR/struct_visualizations")
    parser.add_argument("--alpha", type=float, default=0.5, help="Overlay opacity from 0 to 1 (default: 0.5)")
    args = parser.parse_args()

    if not 0 <= args.alpha <= 1:
        parser.error("--alpha must be between 0 and 1")
    if args.limit < 0:
        parser.error("--limit must be 0 or positive")

    image_dir = args.scene_dir / "undistorted_images"
    mask_dir = args.scene_dir / "struct_mask"
    if not image_dir.is_dir() or not mask_dir.is_dir():
        parser.error(f"Expected undistorted_images/ and struct_mask/ under {args.scene_dir}")

    images = {path.stem: path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in IMAGE_SUFFIXES}
    masks = [mask_dir / f"{Path(args.frame).stem}.png"] if args.frame else sorted(mask_dir.glob("*.png"))
    if args.limit and not args.frame:
        masks = masks[: args.limit]
    if not masks:
        parser.error(f"No mask PNG files found in {mask_dir}")

    output_dir = args.output_dir or args.scene_dir / "struct_visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    for mask_path in masks:
        if not mask_path.is_file():
            parser.error(f"Mask not found: {mask_path}")
        rgb_path = images.get(mask_path.stem)
        if rgb_path is None:
            parser.error(f"No RGB image with stem {mask_path.stem!r} in {image_dir}")
        result = make_comparison(rgb_path, mask_path, args.alpha)
        output_path = output_dir / f"{mask_path.stem}_structure_comparison.png"
        result.save(output_path)
        print(output_path)


if __name__ == "__main__":
    main()
