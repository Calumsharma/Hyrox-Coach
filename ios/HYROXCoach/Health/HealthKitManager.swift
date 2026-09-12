import Foundation
import HealthKit

/// Reads recovery-relevant data (HRV, resting heart rate, sleep, VO2max) directly from
/// Apple Health — no third-party developer account needed, unlike Terra/Whoop/Garmin/Oura.
/// Trade-off: only covers Apple Watch / Health-app data, not other wearable brands directly.
///
/// The Simulator's Health store is empty by default, so every read here will come back nil
/// there — that's expected, not a bug. Real numbers need a real device, ideally with a
/// paired Apple Watch, or sample data manually added to the Simulator's Health app.
@MainActor
final class HealthKitManager {
    static let shared = HealthKitManager()

    private let store = HKHealthStore()

    private let hrvType = HKQuantityType(.heartRateVariabilitySDNN)
    private let restingHRType = HKQuantityType(.restingHeartRate)
    private let vo2MaxType = HKQuantityType(.vo2Max)
    private let sleepType = HKCategoryType(.sleepAnalysis)

    var isAvailable: Bool { HKHealthStore.isHealthDataAvailable() }

    private init() {}

    func requestAuthorization() async throws {
        guard isAvailable else { return }
        let readTypes: Set<HKObjectType> = [hrvType, restingHRType, vo2MaxType, sleepType]
        try await store.requestAuthorization(toShare: [], read: readTypes)
    }

    struct RecoveryInputs {
        var hrvMs: Double?
        var restingHrBpm: Double?
        var sleepScore: Double?
        var vo2Max: Double?
    }

    /// Pulls the most recent day's values it can find. Any value HealthKit doesn't have
    /// (no device, no data yet, permission denied) simply comes back nil — the recovery
    /// engine already treats missing fields gracefully.
    func fetchLatestRecoveryInputs() async -> RecoveryInputs {
        async let hrv = latestQuantity(hrvType, unit: .secondUnit(with: .milli))
        async let restingHR = latestQuantity(restingHRType, unit: .count().unitDivided(by: .minute()))
        async let vo2Max = latestQuantity(vo2MaxType, unit: .literUnit(with: .milli).unitDivided(by: HKUnit.gramUnit(with: .kilo).unitMultiplied(by: .minute())))
        async let sleep = latestSleepScore()
        return await RecoveryInputs(hrvMs: hrv, restingHrBpm: restingHR, sleepScore: sleep, vo2Max: vo2Max)
    }

    private func latestQuantity(_ type: HKQuantityType, unit: HKUnit) async -> Double? {
        guard isAvailable else { return nil }
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
        return await withCheckedContinuation { continuation in
            let query = HKSampleQuery(sampleType: type, predicate: nil, limit: 1, sortDescriptors: [sort]) { _, samples, _ in
                let value = (samples?.first as? HKQuantitySample)?.quantity.doubleValue(for: unit)
                continuation.resume(returning: value)
            }
            store.execute(query)
        }
    }

    /// HealthKit exposes raw sleep-stage samples, not a composite "sleep score" (that's
    /// Apple's own proprietary metric, not exposed via the API). This derives a simple,
    /// clearly-approximate 0-100 proxy from total asleep duration over the last 24 hours —
    /// stated here plainly so it's never confused with a real Apple-calculated score.
    private func latestSleepScore() async -> Double? {
        guard isAvailable else { return nil }
        let start = Calendar.current.date(byAdding: .hour, value: -24, to: Date())!
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let asleepValues: Set<Int> = [
            HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
            HKCategoryValueSleepAnalysis.asleepCore.rawValue,
            HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
            HKCategoryValueSleepAnalysis.asleepREM.rawValue,
        ]

        let totalAsleepSeconds: Double? = await withCheckedContinuation { continuation in
            let query = HKSampleQuery(sampleType: sleepType, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, _ in
                guard let samples = samples as? [HKCategorySample], !samples.isEmpty else {
                    continuation.resume(returning: nil)
                    return
                }
                let seconds = samples
                    .filter { asleepValues.contains($0.value) }
                    .reduce(0.0) { $0 + $1.endDate.timeIntervalSince($1.startDate) }
                continuation.resume(returning: seconds)
            }
            store.execute(query)
        }

        guard let totalAsleepSeconds else { return nil }
        let asleepHours = totalAsleepSeconds / 3600
        let targetHours = 8.0
        return min(100, max(0, (asleepHours / targetHours) * 100))
    }
}
