
use std::env;
use std::fs;

use lineforge_engine::image_processing::*;
use lineforge_engine::vectorize::*;
use lineforge_engine::export::*;
use lineforge_engine::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        eprintln!("Usage: {} <raw_l_file> <width> <height> [--out file] [--turdsize N] [--flat] [--format svg|pdf|eps]", args[0]);
        return Ok(());
    }
    let filename = &args[1];
    let width: usize = args[2].parse()?;
    let height: usize = args[3].parse()?;

    let mut turdsize = 2.0;
    let mut flat = false;
    let mut format = "svg".to_string();
    let mut out_file = String::new();

    let mut i = 4;
    while i < args.len() {
        match args[i].as_str() {
            "--turdsize" => {
                i += 1;
                turdsize = args[i].parse()?;
            }
            "--flat" => flat = true,
            "--format" => {
                i += 1;
                format = args[i].clone();
            }
            "--out" => {
                i += 1;
                out_file = args[i].clone();
            }
            _ => eprintln!("Unknown argument: {}", args[i]),
        }
        i += 1;
    }

    let raw_bytes = fs::read(filename)?;
    
    // Bypass the RGBA and f32 float conversions. 
    // Python already processed the image, so we just read 1-byte L-mode pixels directly.
    // 0 = black (true), 255 = white (false)
    let pixels: Vec<bool> = raw_bytes.into_iter().map(|p| p < 128).collect();
    let binary = lineforge_engine::types::BinaryImage {
        width,
        height,
        pixels,
    };

    let opt = TraceOptions {
        turdsize,
        flat,
        ..Default::default()
    };
    let paths = trace(&binary, &opt);

    let output_bytes = match format.as_str() {
        "svg" => export_svg(&paths, width, height).into_bytes(),
        "pdf" => export_pdf(&paths, width, height),
        "eps" => export_eps(&paths, width, height).into_bytes(),
        _ => {
            eprintln!("Unknown format: {}", format);
            return Ok(());
        }
    };

    if out_file.is_empty() {
        std::io::Write::write_all(&mut std::io::stdout(), &output_bytes)?;
    } else {
        fs::write(&out_file, output_bytes)?;
    }
    Ok(())
}
