
/// Represents a continuous coordinate space for vector calculations
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

/// Node variants that construct vector graphics shapes
#[derive(Debug, Clone, PartialEq)]
pub enum PathNode {
    MoveTo(Point),
    LineTo(Point),
    CurveTo {
        control1: Point,
        control2: Point,
        to: Point,
    },
    Close,
}

/// Contiguous 1D flat layout representation of a Grayscale float image
pub struct GrayscaleImage {
    pub width: usize,
    pub height: usize,
    pub pixels: Vec<f32>, // Normalized intensity values between 0.0 and 1.0
}

/// Contiguous 1D binary mask representation for the vectorizing engine
pub struct BinaryImage {
    pub width: usize,
    pub height: usize,
    pub pixels: Vec<bool>, // true = black (foreground), false = white (background)
}