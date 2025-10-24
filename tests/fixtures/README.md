# Test Fixtures

This directory contains test images for algorithm validation.

## Required Test Images

To run the full validation suite, please add the following test images:

### 1. Single Face Images
- `person_a.jpg` - Single frontal face portrait (male or female)
- `person_b.jpg` - Single frontal face portrait (different person)
- `single_face.jpg` - Any single face portrait

### 2. Couple Images
- `couple.jpg` - Image with exactly 2 faces
- `couple_template.jpg` - Another image with exactly 2 faces
- `husband.jpg` - Single male face portrait
- `wife.jpg` - Single female face portrait

### 3. Edge Cases
- `landscape.jpg` - Landscape/scenery image with no faces
- `low_res_a.jpg`, `low_res_b.jpg` - Low resolution faces (< 512px)
- `side_angle_a.jpg`, `side_angle_b.jpg` - Side profile faces
- `glasses_a.jpg`, `glasses_b.jpg` - Faces with glasses
- `dark_a.jpg`, `bright_b.jpg` - Different lighting conditions

### 4. Special Cases (Optional)
- `anime_a.png`, `anime_b.png` - Anime/ACG style faces
- `old_a.jpg`, `young_b.jpg` - Different age groups
- `smile_a.jpg`, `serious_b.jpg` - Different expressions
- `group_a.jpg`, `group_b.jpg` - Group photos with multiple faces

## Image Requirements

- **Format:** JPG or PNG
- **Resolution:** 512x512 to 2048x2048 pixels (typical)
- **Face Size:** At least 128x128 pixels for face detection
- **Quality:** Clear, not too blurry

## Where to Get Test Images

### Option 1: Use Your Own Photos
- Take photos with your phone camera
- Ensure good lighting and clear faces
- Get consent if using photos of others

### Option 2: Use Free Stock Photos
- [Unsplash](https://unsplash.com/s/photos/portrait)
- [Pexels](https://www.pexels.com/search/portrait/)
- [Pixabay](https://pixabay.com/images/search/portrait/)

### Option 3: Generate Synthetic Faces
- [This Person Does Not Exist](https://thispersondoesnotexist.com/)
- Generate multiple unique faces for testing

## Privacy Note

⚠️ **Important:** Do NOT commit real personal photos to the repository if it's public. These test fixtures should be:
- Personal photos (kept locally, added to .gitignore)
- Stock photos (with appropriate licenses)
- Synthetic/generated faces

## Usage

Once test images are added, run the validation script:

```bash
python scripts/validate_algorithm.py
```

The script will:
1. Detect available test fixtures
2. Run face-swap tests on each pair
3. Save results to `tests/validation_results/`
4. Generate performance benchmarks

## Validation Results

Results will be saved to `tests/validation_results/` with filenames like:
- `result_high_quality_frontal_face.jpg`
- `result_side_angle_faces.jpg`
- etc.

Review these results manually for visual quality assessment.

## .gitignore

The following pattern is added to `.gitignore` to avoid committing test images:

```
tests/fixtures/*.jpg
tests/fixtures/*.png
tests/validation_results/
```

Only this README will be tracked in version control.
