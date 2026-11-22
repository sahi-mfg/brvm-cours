import PDFKit
// dump: page \t x0 \t y0 \t x1 \t y1 \t char ; uses per-line selections then per-char selection for consistent bounds
let d = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
let only = CommandLine.arguments.count > 2 ? Int(CommandLine.arguments[2])! : 0
var out = ""
for p in 0..<d.pageCount {
  if only > 0 && p+1 != only { continue }
  guard let pg = d.page(at:p) else { continue }
  guard let full = pg.string else { continue }
  let ns = full as NSString
  for i in 0..<ns.length {
    let c = ns.substring(with: NSRange(location:i, length:1))
    if c.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { continue }
    guard let s = pg.selection(for: NSRange(location:i, length:1)) else { continue }
    let b = s.bounds(for: pg)
    out += "\(p+1)\t\(String(format:"%.1f",b.minX))\t\(String(format:"%.1f",b.minY))\t\(String(format:"%.1f",b.maxX))\t\(String(format:"%.1f",b.maxY))\t\(c)\n"
  }
}
print(out, terminator:"")
