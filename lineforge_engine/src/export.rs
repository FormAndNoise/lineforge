// ============================================================
// FILE: src/export.rs
// ============================================================

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
        "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 {w} {h}\" width=\"{w}\" height=\"{h}\">\n  <path d=\"{data}\" fill=\"black\" fill-rule=\"evenodd\"/>\n</svg>",
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
                PathNode::MoveTo(p) => stream.push_str(&format!("{} {} m\n", p.x, height as f64 - p.y)),
                PathNode::LineTo(p) => stream.push_str(&format!("{} {} l\n", p.x, height as f64 - p.y)),
                PathNode::CurveTo {
                    control1,
                    control2,
                    to,
                } => stream.push_str(&format!(
                    "{} {} {} {} {} {} c\n",
                    control1.x, height as f64 - control1.y,
                    control2.x, height as f64 - control2.y,
                    to.x, height as f64 - to.y
                )),
                PathNode::Close => stream.push_str("h\n"),
            }
        }
    }
    stream.push_str("f\n");
    let stream_bytes = stream.into_bytes();

    let mut pdf = Vec::new();
    let mut offsets = Vec::new();

    // Index 0 is a dummy offset for the free list
    offsets.push(0);

    // Header
    let header = b"%PDF-1.4\n";
    pdf.extend_from_slice(header);

    // Object 1: Catalog
    offsets.push(pdf.len());
    pdf.extend_from_slice(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n");

    // Object 2: Pages
    offsets.push(pdf.len());
    pdf.extend_from_slice(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n");

    // Object 3: Page
    offsets.push(pdf.len());
    let obj3 = format!(
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {} {}] /Contents 4 0 R /Resources << >> >> endobj\n",
        width, height
    );
    pdf.extend_from_slice(obj3.as_bytes());

    // Object 4: Content Stream
    offsets.push(pdf.len());
    let obj4_start = format!(
        "4 0 obj\n<< /Length {} >>\nstream\n",
        stream_bytes.len()
    );
    pdf.extend_from_slice(obj4_start.as_bytes());
    pdf.extend_from_slice(&stream_bytes);
    pdf.extend_from_slice(b"endstream\nendobj\n");

    // Cross-Reference Table
    let xref_start = pdf.len();
    pdf.extend_from_slice(b"xref\n0 5\n");
    pdf.extend_from_slice(b"0000000000 65535 f \n");
    
    // Generate valid 10-digit byte offsets
    for i in 1..=4 {
        let entry = format!("{:010} 00000 n \n", offsets[i]);
        pdf.extend_from_slice(entry.as_bytes());
    }

    // Trailer
    let trailer = format!(
        "trailer << /Size 5 /Root 1 0 R >>\nstartxref\n{}\n%%EOF",
        xref_start
    );
    pdf.extend_from_slice(trailer.as_bytes());

    pdf
}

/// Section 5.3: EPS export
pub fn export_eps(paths: &[Vec<PathNode>], width: usize, height: usize) -> String {
    let mut ops = String::new();
    for path in paths {
        for node in path {
            match node {
                PathNode::MoveTo(p) => ops.push_str(&format!("{} {} moveto\n", p.x, height as f64 - p.y)),
                PathNode::LineTo(p) => ops.push_str(&format!("{} {} lineto\n", p.x, height as f64 - p.y)),
                PathNode::CurveTo {
                    control1,
                    control2,
                    to,
                } => ops.push_str(&format!(
                    "{} {} {} {} {} {} curveto\n",
                    control1.x, height as f64 - control1.y,
                    control2.x, height as f64 - control2.y,
                    to.x, height as f64 - to.y
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