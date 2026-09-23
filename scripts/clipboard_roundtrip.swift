// Local validation helper. Preserve every available clipboard format in memory.
import AppKit
import Foundation

let board = NSPasteboard.general
let initialCount = board.changeCount
var saved: [NSPasteboardItem] = []
for item in board.pasteboardItems ?? [] {
    let copy = NSPasteboardItem()
    for type in item.types {
        guard let data = item.data(forType: type) else {
            fatalError("Cannot preserve a clipboard format; clipboard left untouched")
        }
        copy.setData(data, forType: type)
    }
    saved.append(copy)
}
guard board.changeCount == initialCount else {
    fatalError("Clipboard changed during snapshot; clipboard left untouched")
}
let source = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8)
board.clearContents()
let written = board.setString(source, forType: .string)
let ourCount = board.changeCount
defer {
    // Never overwrite a newer clipboard value placed there by the user.
    if board.changeCount == ourCount {
        board.clearContents()
        if !saved.isEmpty { board.writeObjects(saved) }
    }
}
guard written, let returned = board.string(forType: .string) else {
    throw NSError(domain: "ClipboardRoundtrip", code: 1)
}
try returned.write(toFile: CommandLine.arguments[2], atomically: true, encoding: .utf8)
