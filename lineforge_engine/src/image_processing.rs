
use crate::types::*;

/// Section 3.1: Strip alpha & convert RGBA to gray float.
pub fn rgba_to_grayscale(rgba: &[u8], width: usize, height: usize) -> GrayscaleImage {
    assert_eq!(rgba.len(), width * height * 4);
    let mut pixels = Vec::with_capacity(width * height);
    for chunk in rgba.chunks_exact(4) {
        let r = chunk[0] as f32 / 255.0;
        let g = chunk[1] as f32 / 255.0;
        let b = chunk[2] as f32 / 255.0;
        let a = chunk[3] as f32 / 255.0;

        // Blend against white background
        let blend = |c: f32| c * a + 1.0 * (1.0 - a);
        let rf = blend(r);
        let gf = blend(g);
        let bf = blend(b);

        let gray = 0.2126 * rf + 0.7152 * gf + 0.0722 * bf;
        pixels.push(gray);
    }
    GrayscaleImage {
        width,
        height,
        pixels,
    }
}

/// Section 3.2: Negate (in-place)
pub fn negate(image: &mut GrayscaleImage) {
    for p in &mut image.pixels {
        *p = 1.0 - *p;
    }
}

/// Section 3.3: Threshold to BinaryImage
pub fn threshold(image: &GrayscaleImage, t: f32) -> BinaryImage {
    let pixels: Vec<bool> = image.pixels.iter().map(|&p| p < t).collect();
    BinaryImage {
        width: image.width,
        height: image.height,
        pixels,
    }
}

/// Section 3.4: Median Filter (N x N) with mirrored boundary
pub fn median_filter(image: &GrayscaleImage, n: usize) -> GrayscaleImage {
    assert!(n % 2 == 1, "N must be odd");
    let r = n / 2;
    let width = image.width;
    let height = image.height;
    let mut out = vec![0.0f32; width * height];
    let mut neighbourhood = Vec::with_capacity(n * n);

    for y in 0..height {
        for x in 0..width {
            neighbourhood.clear();
            for dy in -(r as isize)..=(r as isize) {
                let sy = mirror_coord(y as isize + dy, height);
                for dx in -(r as isize)..=(r as isize) {
                    let sx = mirror_coord(x as isize + dx, width);
                    neighbourhood.push(image.pixels[sy * width + sx]);
                }
            }
            neighbourhood.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());
            let median = neighbourhood[neighbourhood.len() / 2];
            out[y * width + x] = median;
        }
    }
    GrayscaleImage {
        width,
        height,
        pixels: out,
    }
}

fn mirror_coord(coord: isize, max: usize) -> usize {
    let max = max as isize;
    let val = if coord < 0 {
        -coord
    } else if coord >= max {
        2 * max - coord - 2
    } else {
        coord
    };
    val as usize
}

/// Section 3.5: Separable Gaussian Blur
pub fn gaussian_blur(image: &GrayscaleImage, sigma: f32) -> GrayscaleImage {
    let r = (3.0 * sigma).ceil() as isize;
    let kernel = gaussian_kernel(sigma, r);
    let width = image.width;
    let height = image.height;

    // Horizontal pass into temp
    let mut temp = vec![0.0f32; width * height];
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0;
            for (k, &w) in kernel.iter().enumerate() {
                let dx = k as isize - r;
                let sx = clamp_coord(x as isize + dx, width);
                sum += image.pixels[y * width + sx] * w;
            }
            temp[y * width + x] = sum;
        }
    }

    // Vertical pass into output
    let mut out = vec![0.0f32; width * height];
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0;
            for (k, &w) in kernel.iter().enumerate() {
                let dy = k as isize - r;
                let sy = clamp_coord(y as isize + dy, height);
                sum += temp[sy * width + x] * w;
            }
            out[y * width + x] = sum;
        }
    }
    GrayscaleImage {
        width,
        height,
        pixels: out,
    }
}

fn gaussian_kernel(sigma: f32, r: isize) -> Vec<f32> {
    let two_sigma2 = 2.0 * sigma * sigma;
    let mut weights = Vec::new();
    for d in -r..=r {
        let w = (-(d * d) as f32 / two_sigma2).exp();
        weights.push(w);
    }
    let sum: f32 = weights.iter().sum();
    weights.iter_mut().for_each(|w| *w /= sum);
    weights
}

fn clamp_coord(coord: isize, max: usize) -> usize {
    let max = max as isize;
    if coord < 0 {
        0
    } else if coord >= max {
        (max - 1) as usize
    } else {
        coord as usize
    }
}

/// Section 3.6: Auto-Level
pub fn auto_level(image: &mut GrayscaleImage) {
    let (min, max) = image
        .pixels
        .iter()
        .fold((f32::MAX, f32::MIN), |(min, max), &p| (min.min(p), max.max(p)));
    if (max - min).abs() < f32::EPSILON {
        return;
    }
    let range = max - min;
    for p in &mut image.pixels {
        *p = (*p - min) / range;
    }
}

/// Section 3.7: Contrast-Stretch
pub fn contrast_stretch(image: &mut GrayscaleImage, p_low: f32, p_high: f32) {
    let total = (image.width * image.height) as f32;
    let count_low = (total * p_low).floor() as usize;
    let count_high = (total * p_high).floor() as usize;

    // Build histogram of 256 bins
    let mut hist = [0usize; 256];
    for &p in &image.pixels {
        let bin = (p * 255.0).round() as usize;
        let bin = bin.min(255);
        hist[bin] += 1;
    }

    let v_low = find_threshold_from_histogram(&hist, count_low, true);
    let v_high = find_threshold_from_histogram(&hist, count_high, false);

    if v_low >= v_high {
        return;
    }
    let range = v_high - v_low;
    for p in &mut image.pixels {
        *p = ((*p - v_low) / range).max(0.0).min(1.0);
    }
}

fn find_threshold_from_histogram(hist: &[usize; 256], target: usize, from_low: bool) -> f32 {
    let mut cum = 0;
    if from_low {
        for (i, &count) in hist.iter().enumerate() {
            cum += count;
            if cum >= target {
                return i as f32 / 255.0;
            }
        }
        1.0
    } else {
        for i in (0..256).rev() {
            cum += hist[i];
            if cum >= target {
                return i as f32 / 255.0;
            }
        }
        0.0
    }
}