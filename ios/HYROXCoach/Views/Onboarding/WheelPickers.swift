import SwiftUI

/// Concrete & Chalk stat-entry controls — scroll wheels instead of typed text, matching the
/// rest of the athlete profile's industrial styling. A wheel can't represent "empty" the way a
/// text field can, so every optional stat here starts at a sensible default the first time its
/// row appears rather than staying truly blank — the athlete can leave it as-is or scroll to
/// their real number, but there's no way to submit "unset" once a wheel is showing a value.

private func wheelLabel(_ text: String) -> some View {
    Text(text.uppercased())
        .font(.system(size: 11, weight: .bold))
        .tracking(1.2)
        .foregroundStyle(Theme.mutedInk)
}

private func wheelUnit(_ text: String) -> some View {
    Text(text)
        .font(.system(size: 13, weight: .semibold))
        .foregroundStyle(Theme.mutedInk)
}

/// Minutes/seconds wheel pair bound to a total-seconds value, e.g. race and split times.
struct WheelTimePicker: View {
    let label: String
    @Binding var seconds: Int?
    var defaultSeconds: Int = 300
    var maxMinutes: Int = 180

    private var resolvedSeconds: Int { seconds ?? defaultSeconds }

    private var minutesBinding: Binding<Int> {
        Binding(get: { resolvedSeconds / 60 }, set: { seconds = $0 * 60 + (resolvedSeconds % 60) })
    }
    private var secondsBinding: Binding<Int> {
        Binding(get: { resolvedSeconds % 60 }, set: { seconds = (resolvedSeconds / 60) * 60 + $0 })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            wheelLabel(label)
            HStack(spacing: 2) {
                Picker("", selection: minutesBinding) {
                    ForEach(0...maxMinutes, id: \.self) { Text("\($0)").tag($0) }
                }
                .pickerStyle(.wheel)
                wheelUnit("min")
                Picker("", selection: secondsBinding) {
                    ForEach(0..<60, id: \.self) { Text(String(format: "%02d", $0)).tag($0) }
                }
                .pickerStyle(.wheel)
                wheelUnit("sec")
            }
            .frame(height: 96)
        }
        .onAppear { if seconds == nil { seconds = defaultSeconds } }
    }
}

/// A single integer wheel with a unit label — age, tested max HR, etc.
struct WheelIntPicker: View {
    let label: String
    @Binding var value: Int?
    let range: ClosedRange<Int>
    let unit: String
    var defaultValue: Int

    private var resolved: Binding<Int> {
        Binding(get: { value ?? defaultValue }, set: { value = $0 })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            wheelLabel(label)
            HStack(spacing: 6) {
                Picker("", selection: resolved) {
                    ForEach(Array(range), id: \.self) { Text("\($0)").tag($0) }
                }
                .pickerStyle(.wheel)
                wheelUnit(unit)
            }
            .frame(height: 96)
        }
        .onAppear { if value == nil { value = defaultValue } }
    }
}

// MARK: - Unit conversion constants

private let kgPerLb = 0.45359237       // exact, by definition
private let lbPerStone = 14.0
private let cmPerInch = 2.54           // exact, by definition

// MARK: - Weight (kg / lb / stone)

enum WeightUnit: String, CaseIterable, Identifiable {
    case kg, lb, stone
    var id: String { rawValue }
    var label: String {
        switch self {
        case .kg: return "KG"
        case .lb: return "LB"
        case .stone: return "STONE"
        }
    }
}

/// Weight stored in kg (0.1 precision) but enterable in kg, lb, or stone — the athlete picks
/// whichever unit they think in, the wheel(s) below switch to match, and the value converts
/// back to kg for storage either way.
struct WeightPicker: View {
    let label: String
    @Binding var weightKg: Double
    @State private var unit: WeightUnit = .kg

    // kg: 30.0-200.0 in 0.1 steps, generated from an integer range so the "nearest tick"
    // lookup below always lands on a bit-identical Double to what's in this array.
    private static let kgTicks: [Double] = (300...2000).map { Double($0) / 10.0 }
    private static let lbTicks: [Double] = (660...4400).map { Double($0) / 10.0 } // 0.1 lb steps

    private var kgBinding: Binding<Double> {
        Binding(
            get: { Double(Int((weightKg * 10).rounded().clamped(300, 2000))) / 10.0 },
            set: { weightKg = $0 }
        )
    }

    private var lbBinding: Binding<Double> {
        Binding(
            get: {
                let lb = weightKg / kgPerLb
                return Double(Int((lb * 10).rounded().clamped(660, 4400))) / 10.0
            },
            set: { weightKg = $0 * kgPerLb }
        )
    }

    private var stoneWhole: Int { Int(((weightKg / kgPerLb) / lbPerStone).rounded(.down)) }
    private var stoneRemainderLb: Int {
        let remainder = Int(((weightKg / kgPerLb) - Double(stoneWhole) * lbPerStone).rounded())
        return remainder >= 14 ? 0 : remainder // 13.6 lb rounds to 14 — that's really the next stone
    }

    private var stoneBinding: Binding<Int> {
        Binding(
            get: { stoneWhole.clamped(0, 40) },
            set: { weightKg = (Double($0) * lbPerStone + Double(stoneRemainderLb)) * kgPerLb }
        )
    }
    private var stoneLbBinding: Binding<Int> {
        Binding(
            get: { stoneRemainderLb },
            set: { weightKg = (Double(stoneWhole) * lbPerStone + Double($0)) * kgPerLb }
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            wheelLabel(label)

            Picker("", selection: $unit) {
                ForEach(WeightUnit.allCases) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)

            Group {
                switch unit {
                case .kg:
                    HStack(spacing: 6) {
                        Picker("", selection: kgBinding) {
                            ForEach(Self.kgTicks, id: \.self) { Text(String(format: "%.1f", $0)).tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("kg")
                    }
                case .lb:
                    HStack(spacing: 6) {
                        Picker("", selection: lbBinding) {
                            ForEach(Self.lbTicks, id: \.self) { Text(String(format: "%.1f", $0)).tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("lb")
                    }
                case .stone:
                    HStack(spacing: 2) {
                        Picker("", selection: stoneBinding) {
                            ForEach(0...40, id: \.self) { Text("\($0)").tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("st")
                        Picker("", selection: stoneLbBinding) {
                            ForEach(0..<14, id: \.self) { Text("\($0)").tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("lb")
                    }
                }
            }
            .frame(height: 96)
        }
    }
}

// MARK: - Height (cm / ft+in)

enum HeightUnit: String, CaseIterable, Identifiable {
    case cm, ftin
    var id: String { rawValue }
    var label: String { self == .cm ? "CM" : "FT/IN" }
}

/// Height stored in cm but enterable in cm or feet+inches.
struct HeightPicker: View {
    let label: String
    @Binding var heightCm: Double
    @State private var unit: HeightUnit = .cm

    private var cmBinding: Binding<Int> {
        Binding(
            get: { Int(heightCm.rounded()).clamped(120, 230) },
            set: { heightCm = Double($0) }
        )
    }

    private var totalInches: Int { Int((heightCm / cmPerInch).rounded()) }
    private var feet: Int { (totalInches / 12).clamped(3, 7) }
    private var inches: Int { totalInches % 12 }

    private var feetBinding: Binding<Int> {
        Binding(get: { feet }, set: { heightCm = Double($0 * 12 + inches) * cmPerInch })
    }
    private var inchesBinding: Binding<Int> {
        Binding(get: { inches }, set: { heightCm = Double(feet * 12 + $0) * cmPerInch })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            wheelLabel(label)

            Picker("", selection: $unit) {
                ForEach(HeightUnit.allCases) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)

            Group {
                switch unit {
                case .cm:
                    HStack(spacing: 6) {
                        Picker("", selection: cmBinding) {
                            ForEach(120...230, id: \.self) { Text("\($0)").tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("cm")
                    }
                case .ftin:
                    HStack(spacing: 2) {
                        Picker("", selection: feetBinding) {
                            ForEach(3...7, id: \.self) { Text("\($0)").tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("ft")
                        Picker("", selection: inchesBinding) {
                            ForEach(0..<12, id: \.self) { Text("\($0)").tag($0) }
                        }
                        .pickerStyle(.wheel)
                        wheelUnit("in")
                    }
                }
            }
            .frame(height: 96)
        }
    }
}

private extension Int {
    func clamped(_ low: Int, _ high: Int) -> Int { Swift.min(Swift.max(self, low), high) }
}
private extension Double {
    func clamped(_ low: Double, _ high: Double) -> Double { Swift.min(Swift.max(self, low), high) }
}
