
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



/// Section 3.3: Threshold to BinaryImage
pub fn threshold(image: &GrayscaleImage, t: f32) -> BinaryImage {
    let pixels: Vec<bool> = image.pixels.iter().map(|&p| p < t).collect();
    BinaryImage {
        width: image.width,
        height: image.height,
        pixels,
    }
}
