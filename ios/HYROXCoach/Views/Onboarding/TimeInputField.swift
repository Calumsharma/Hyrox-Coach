import SwiftUI

/// A "mm:ss" text field bound to an optional seconds value.
struct TimeInputField: View {
    let label: String
    @Binding var seconds: Int?
    @State private var text: String = ""

    var body: some View {
        HStack {
            Text(label)
            Spacer()
            TextField("mm:ss", text: $text)
                .multilineTextAlignment(.trailing)
                .keyboardType(.numbersAndPunctuation)
                .frame(width: 90)
                .onAppear { text = Self.format(seconds) }
                .onChange(of: text) { _, newValue in
                    seconds = Self.parse(newValue)
                }
        }
    }

    static func format(_ seconds: Int?) -> String {
        guard let seconds else { return "" }
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }

    static func parse(_ text: String) -> Int? {
        let parts = text.split(separator: ":")
        guard parts.count == 2,
              let minutes = Int(parts[0]),
              let secs = Int(parts[1]) else { return nil }
        return minutes * 60 + secs
    }
}
