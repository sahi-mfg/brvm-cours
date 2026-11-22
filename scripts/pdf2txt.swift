import PDFKit
// usage: swift pdf2txt.swift in.pdf out.txt [in2.pdf out2.txt ...]
let a = Array(CommandLine.arguments.dropFirst())
var i = 0
while i+1 < a.count {
  if let d = PDFDocument(url: URL(fileURLWithPath: a[i])) {
    var s = ""
    for p in 0..<d.pageCount { s += "\n=== PAGE \(p+1)\n" + (d.page(at:p)?.string ?? "") }
    try? s.write(toFile: a[i+1], atomically: true, encoding: .utf8)
  } else { FileManager.default.createFile(atPath: a[i+1]+".err", contents: nil) }
  i += 2
}
