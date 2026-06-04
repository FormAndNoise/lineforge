
use crate::types::*;

pub struct TraceOptions {
    pub turdsize: f64,
    pub flat: bool,
    pub epsilon: f64,
    pub angle_threshold: f64,
}

impl Default for TraceOptions {
    fn default() -> Self {
        Self {
            turdsize: 2.0,
            flat: false,
            epsilon: 0.5,
            angle_threshold: 0.5,
        }
    }
}

/// Section 4: Full vectorization pipeline
pub fn trace(mask: &BinaryImage, opt: &TraceOptions) -> Vec<Vec<PathNode>> {
    let mut visited = vec![false; mask.width * mask.height];
    let mut paths = Vec::new();

    // Scan for black pixels not yet visited
    for y in 0..mask.height {
        for x in 0..mask.width {
            if mask.pixels[y * mask.width + x] && !visited[y * mask.width + x] {
                let loop_points = trace_moore_boundary(mask, x, y, &mut visited);
                if loop_points.len() < 3 {
                    continue;
                }
                let area = polygon_area(&loop_points);
                if area < opt.turdsize {
                    continue; // discard turd
                }
                let simplified = douglas_peucker(&loop_points, opt.epsilon);
                let nodes = curve_fit(&simplified, opt);
                paths.push(nodes);
            }
        }
    }
    paths
}

/// Section 4.1: Moore-Neighbor boundary tracing
fn trace_moore_boundary(
    mask: &BinaryImage,
    start_x: usize,
    start_y: usize,
    visited: &mut [bool],
) -> Vec<Point> {
    let width = mask.width;
    let height = mask.height;

    // Directions: 0=E, 1=SE, 2=S, 3=SW, 4=W, 5=NW, 6=N, 7=NE
    const DX: [isize; 8] = [1, 1, 0, -1, -1, -1, 0, 1];
    const DY: [isize; 8] = [0, 1, 1, 1, 0, -1, -1, -1];

    let mut path = Vec::new();
    let mut cx = start_x as isize;
    let mut cy = start_y as isize;
    let start_dir = 4; // start by looking west (backtrack)
    let mut dir = start_dir;

    // Find the first boundary point to start (the leftmost black pixel in the first row of the component)
    // We start from the pixel found and move clockwise.
    // Mark the starting pixel as visited
    visited[start_y * width + start_x] = true;
    path.push(Point {
        x: cx as f64,
        y: cy as f64,
    });

    // Moore neighbor tracing: we look at the 8 neighbors starting from the opposite of the incoming direction.
    // Standard algorithm: we arrived from direction dir, look clockwise starting from (dir+5)%8 to find next black pixel.
    let mut first = true;
    loop {
        // Determine the start of search: for the first step, look clockwise from the starting direction (W=4)
        let search_start = if first { 0 } else { (dir + 5) % 8 };
        first = false;

        let mut next_dir = 8; // invalid
        for i in 0..8 {
            let ndir = (search_start + i) % 8;
            let nx = cx + DX[ndir];
            let ny = cy + DY[ndir];
            if nx >= 0 && nx < width as isize && ny >= 0 && ny < height as isize {
                if mask.pixels[ny as usize * width + nx as usize] {
                    next_dir = ndir;
                    break;
                }
            }
        }
        if next_dir == 8 {
            break; // isolated pixel?
        }

        // Move to the found neighbor
        cx += DX[next_dir];
        cy += DY[next_dir];
        dir = next_dir;

        // Mark the pixel visited
        let idx = cy as usize * width + cx as usize;
        if !visited[idx] {
            visited[idx] = true;
            path.push(Point {
                x: cx as f64,
                y: cy as f64,
            });
        } else if cx == start_x as isize && cy == start_y as isize {
            break; // back to start
        }
    }

    // Close the loop by repeating the start point at the end (shoelace expects closed polygon)
    if path.len() > 1 && (path.last().unwrap().x != path[0].x || path.last().unwrap().y != path[0].y) {
        path.push(path[0]);
    }
    path
}

/// Shoelace polygon area
fn polygon_area(pts: &[Point]) -> f64 {
    let n = pts.len();
    if n < 3 {
        return 0.0;
    }
    let mut area = 0.0;
    for i in 0..n {
        let j = (i + 1) % n;
        area += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
    }
    0.5 * area.abs()
}

/// Section 4.2: Douglas-Peucker simplification
fn douglas_peucker(points: &[Point], epsilon: f64) -> Vec<Point> {
    if points.len() <= 2 {
        return points.to_vec();
    }
    let start = points[0];
    let end = points[points.len() - 1];

    // Find point with max perpendicular distance
    let mut max_dist = 0.0;
    let mut max_idx = 0;
    for i in 1..points.len() - 1 {
        let d = perpendicular_distance(points[i], start, end);
        if d > max_dist {
            max_dist = d;
            max_idx = i;
        }
    }

    if max_dist > epsilon {
        // Recursively simplify both halves
        let mut left = douglas_peucker(&points[..=max_idx], epsilon);
        let mut right = douglas_peucker(&points[max_idx..], epsilon);
        // Combine, skipping the duplicate point at the split
        left.pop();
        left.append(&mut right);
        left
    } else {
        vec![start, end]
    }
}

/// Perpendicular distance from point p to line segment a-b
fn perpendicular_distance(p: Point, a: Point, b: Point) -> f64 {
    let num = ((b.y - a.y) * p.x - (b.x - a.x) * p.y + b.x * a.y - b.y * a.x).abs();
    let den = ((b.y - a.y).powi(2) + (b.x - a.x).powi(2)).sqrt();
    if den < 1e-9 {
        // a and b are the same point
        ((p.x - a.x).powi(2) + (p.y - a.y).powi(2)).sqrt()
    } else {
        num / den
    }
}

/// Section 4.3: Corner detection & Bezier fitting
fn curve_fit(points: &[Point], opt: &TraceOptions) -> Vec<PathNode> {
    if points.len() < 2 {
        return vec![];
    }
    let mut nodes = Vec::new();
    nodes.push(PathNode::MoveTo(points[0]));

    if opt.flat {
        for pt in &points[1..] {
            nodes.push(PathNode::LineTo(*pt));
        }
        // close if first == last?
    } else {
        // Process segment by segment, detecting corners
        let mut i = 1;
        while i < points.len() {
            if i < points.len() - 1 {
                let prev = points[i - 1];
                let curr = points[i];
                let next = points[i + 1];

                let v1 = Point {
                    x: curr.x - prev.x,
                    y: curr.y - prev.y,
                };
                let v2 = Point {
                    x: next.x - curr.x,
                    y: next.y - curr.y,
                };
                let mag1 = (v1.x.powi(2) + v1.y.powi(2)).sqrt();
                let mag2 = (v2.x.powi(2) + v2.y.powi(2)).sqrt();
                let cos_theta = if mag1 < 1e-9 || mag2 < 1e-9 {
                    1.0 // treat as straight
                } else {
                    (v1.x * v2.x + v1.y * v2.y) / (mag1 * mag2)
                };
                let theta = cos_theta.acos();

                if theta > opt.angle_threshold {
                    // Sharp corner: line to current point
                    nodes.push(PathNode::LineTo(curr));
                    i += 1;
                } else {
                    // Smooth segment: fit cubic Bezier using least-squares method (sec 4.3 formula)
                    // Here we use the simple heuristic: C1 = P_B + V1/3, C2 = P_C - V2/3
                    let c1 = Point {
                        x: curr.x + v1.x / 3.0,
                        y: curr.y + v1.y / 3.0,
                    };
                    let c2 = Point {
                        x: next.x - v2.x / 3.0,
                        y: next.y - v2.y / 3.0,
                    };
                    nodes.push(PathNode::CurveTo {
                        control1: c1,
                        control2: c2,
                        to: next,
                    });
                    i += 2;
                }
            } else {
                // Last point: just line to it
                nodes.push(PathNode::LineTo(points[i]));
                i += 1;
            }
        }
    }
    // If the loop is closed (first point equals last), add Close
    if nodes.len() > 1 {
        let first = match &nodes[0] {
            PathNode::MoveTo(p) => *p,
            _ => unreachable!(),
        };
        let last = match &nodes[nodes.len() - 1] {
            PathNode::LineTo(p) => *p,
            PathNode::CurveTo { to, .. } => *to,
            PathNode::Close => first, // already closed
            _ => unreachable!(),
        };
        if (first.x - last.x).abs() < 1e-6 && (first.y - last.y).abs() < 1e-6 {
            // The last explicit point is the same as the start; replace it with Close
            nodes.pop();
            nodes.push(PathNode::Close);
        }
    }
    nodes
}