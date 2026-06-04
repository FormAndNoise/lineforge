
#[cfg(test)]
mod tests {
    use crate::image_processing::*;
    use crate::vectorize::*;
    use crate::export::*;
    use crate::types::*;

    // Vector A: RGBA to Grayscale (Section 3.1)
    #[test]
    fn test_rgba_to_grayscale() {
        let input: [u8; 16] = [
            0, 0, 0, 255,        // black
            255, 255, 255, 255,  // white
            255, 0, 0, 128,      // translucent red
            0, 255, 0, 0         // fully transparent green
        ];
        let gray = rgba_to_grayscale(&input, 2, 2);
        let expected = vec![0.0, 1.0, 0.6048, 1.0];
        for (a, e) in gray.pixels.iter().zip(expected.iter()) {
            assert!((a - e).abs() < 0.001, "expected {}, got {}", e, a);
        }
    }

    // Vector B: Median filter & Gaussian blur
    #[test]
    fn test_median_filter() {
        let pixels: Vec<f32> = vec![
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 1.0, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
        ];
        let img = GrayscaleImage { width: 5, height: 5, pixels };
        let filtered = median_filter(&img, 3);
        // All values should be 0.5
        for p in &filtered.pixels {
            assert!((p - 0.5).abs() < 0.001);
        }
    }

    #[test]
    fn test_gaussian_blur() {
        let pixels: Vec<f32> = vec![
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 1.0, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5,
        ];
        let img = GrayscaleImage { width: 5, height: 5, pixels };
        let blurred = gaussian_blur(&img, 1.0);
        let center = blurred.pixels[2 * 5 + 2];
        // Expected ~0.57943
        assert!((center - 0.57943).abs() < 0.01);
    }

    // Vector C: Trace, flat and curved
    #[test]
    fn test_trace_flat() {
        let binary = BinaryImage {
            width: 6,
            height: 6,
            pixels: vec![
                false, false, false, false, false, false,
                false, false, false, false, false, false,
                false, false, true,  true,  false, false,
                false, false, true,  true,  false, false,
                false, false, false, false, false, false,
                false, false, false, false, false, false,
            ],
        };
        let opt = TraceOptions { flat: true, ..Default::default() };
        let paths = trace(&binary, &opt);
        let expected = vec![
            PathNode::MoveTo(Point { x: 2.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 4.0 }),
            PathNode::LineTo(Point { x: 2.0, y: 4.0 }),
            PathNode::Close,
        ];
        assert_eq!(paths.len(), 1);
        assert_eq!(paths[0], expected);
    }

    #[test]
    fn test_trace_curved() {
        // Same square, but with angle > 0.5, so corners remain line-to.
        let binary = BinaryImage {
            width: 6,
            height: 6,
            pixels: vec![
                false, false, false, false, false, false,
                false, false, false, false, false, false,
                false, false, true,  true,  false, false,
                false, false, true,  true,  false, false,
                false, false, false, false, false, false,
                false, false, false, false, false, false,
            ],
        };
        let opt = TraceOptions::default(); // flat=false, angle_threshold=0.5
        let paths = trace(&binary, &opt);
        // Since corner is 90 deg > 0.5 rad, it yields line-to segments.
        let expected = vec![
            PathNode::MoveTo(Point { x: 2.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 4.0 }),
            PathNode::LineTo(Point { x: 2.0, y: 4.0 }),
            PathNode::Close,
        ];
        assert_eq!(paths.len(), 1);
        assert_eq!(paths[0], expected);
    }

    // Export tests
    #[test]
    fn test_svg_export() {
        let nodes = vec![
            PathNode::MoveTo(Point { x: 2.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 4.0 }),
            PathNode::LineTo(Point { x: 2.0, y: 4.0 }),
            PathNode::Close,
        ];
        let svg = export_svg(&[nodes], 6, 6);
        assert!(svg.contains("M 2 2 L 4 2 L 4 4 L 2 4 Z"));
    }

    #[test]
    fn test_eps_export() {
        let nodes = vec![
            PathNode::MoveTo(Point { x: 2.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 2.0 }),
            PathNode::LineTo(Point { x: 4.0, y: 4.0 }),
            PathNode::LineTo(Point { x: 2.0, y: 4.0 }),
            PathNode::Close,
        ];
        let eps = export_eps(&[nodes], 6, 6);
        assert!(eps.contains("2 2 moveto"));
        assert!(eps.contains("4 2 lineto"));
        assert!(eps.contains("4 4 lineto"));
        assert!(eps.contains("2 4 lineto"));
        assert!(eps.contains("closepath"));
    }
}
