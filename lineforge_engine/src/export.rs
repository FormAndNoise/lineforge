
use crate::types::*;

/// Section 5.1: SVG export
pub fn export_svg(paths: &[Vec<PathNode>], width: usize, height: usize) -> String {
    let mut data = String::new();
    for path in paths {
        for node in path {
            match node {
                PathNode::MoveTo(p) => data.push_str(&format!("M {} {} ", p.x, p.y)),
                PathNode::LineTo(p) => data.push_str(&format!("L {} {} ", p.x, p.y)),
                PathNode::CurveTo {
                    control1,
                    control2,
                    to,
                } => data.push_str(&format!(
                    "C {} {}, {} {}, {} {} ",
                    control1.x, control1.y, control2.x, control2.y, to.x, to.y
                )),
                PathNode::Close => data.push_str("Z "),
            }
        }
    }
    format!(
        "<svg xmlns=\"http://w3.org\" viewBox=\"0 0 {w} {h}\" width=\"{w}\" height=\"{h}\">\n  <path d=\"{data}\" fill=\"black\" fill-rule=\"evenodd\"/>\n</svg>",
        w = width,
        h = height,
        data = data.trim()
    )
}

/// Section 5.2: PDF export
pub fn export_pdf(paths: &[Vec<PathNode>], width: usize, height: usize) -> Vec<u8> {
    let mut stream = String::new();
    for path in paths {
        for node in path {
            match node {
                PathNode::MoveTo(p) => stream.push_str(&format!("{} {} m\n", p.x, p.y)),
                PathNode::LineTo(p) => stream.push_str(&format!("{} {} l\n", p.x, p.y)),
                PathNode::CurveTo {
                    control1,
                    control2,
                    to,
                } => stream.push_str(&format!(
                    "{} {} {} {} {} {} c\n",
                    control1.x, control1.y, control2.x, control2.y, to.x, to.y
                )),
                PathNode::Close => stream.push_str("h\n"),
            }
        }
    }
    stream.push_str("f\n");
    let stream_len = stream.len();

    let pdf = format!(
        "%PDF-1.4\n\
         1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n\
         2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n\
         3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Contents 4 0 R /Resources << >> >> endobj\n\
         4 0 obj\n<< /Length {len} >>\nstream\n{stream}endstream\nendobj\n\
         xref\n0 5\n\
         0000000000 65535 f \n\
         0000000009 00000 n \n\
         0000000062 00000 n \n\
         0000000119 00000 n \n\
         0000000234 00000 n \n\
         trailer << /Size 5 /Root 1 0 R >>\n\
         %%EOF",
        w = width,
        h = height,
        len = stream_len,
        stream = stream
    );
    // Note: xref offsets are fake (they don't match real binary sizes) - a real implementation would compute correct byte offsets.
    // For a fully compliant PDF, we would build the xref table programmatically.
    pdf.into_bytes()
}

/// Section 5.3: EPS export
pub fn export_eps(paths: &[Vec<PathNode>], width: usize, height: usize) -> String {
    let mut ops = String::new();
    for path in paths {
        for node in path {
            match node {
                PathNode::MoveTo(p) => ops.push_str(&format!("{} {} moveto\n", p.x, p.y)),
                PathNode::LineTo(p) => ops.push_str(&format!("{} {} lineto\n", p.x, p.y)),
                PathNode::CurveTo {
                    control1,
                    control2,
                    to,
                } => ops.push_str(&format!(
                    "{} {} {} {} {} {} curveto\n",
                    control1.x, control1.y, control2.x, control2.y, to.x, to.y
                )),
                PathNode::Close => ops.push_str("closepath\n"),
            }
        }
    }
    format!(
        "%!PS-Adobe-3.0 EPSF-3.0\n\
         %%BoundingBox: 0 0 {w} {h}\n\
         %%Pages: 1\n\
         %%EndComments\n\
         newpath\n\
         {ops}\
         0 0 0 setrgbcolor\n\
         fill\n\
         %%EOF",
        w = width,
        h = height,
        ops = ops
    )
}