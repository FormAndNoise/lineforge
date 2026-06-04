
use std::env;
use std::fs;

use lineforge_engine::image_processing::*;
use lineforge_engine::vectorize::*;
use lineforge_engine::export::*;
use lineforge_engine::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        eprintln!("Usage: {} <rgba_file> <width> <height> [--turdsize N] [--flat] [--format svg|pdf|eps]", args[0]);
        return Ok(());
    }
    let filename = &args[1];
    let width: usize = args[2].parse()?;
    let height: usize = args[3].parse()?;

    let mut turdsize = 2.0;
    let mut flat = false;
    let mut format = "svg".to_string();

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
            _ => eprintln!("Unknown argument: {}", args[i]),
        }
        i += 1;
    }

    let rgba_bytes = fs::read(filename)?;
    let mut gray = rgba_to_grayscale(&rgba_bytes, width, height);

    // Optional processing pipeline (simplified: just threshold and vectorize)
    // In a real tool you'd add filter flags.
    // For demo, apply a median filter to clean noise, then threshold at 0.5.
    gray = median_filter(&gray, 3);
    let binary = threshold(&gray, 0.5);

    let opt = TraceOptions {
        turdsize,
        flat,
        ..Default::default()
    };
    let paths = trace(&binary, &opt);

    match format.as_str() {
        "svg" => println!("{}", export_svg(&paths, width, height)),
        "pdf" => {
            let pdf = export_pdf(&paths, width, height);
            std::io::Write::write_all(&mut std::io::stdout(), &pdf)?;
        }
        "eps" => println!("{}", export_eps(&paths, width, height)),
        _ => eprintln!("Unknown format: {}", format),
    }
    Ok(())
}
