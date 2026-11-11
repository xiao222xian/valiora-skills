// Apple AUSoundIsolation 离线人声隔离：isolate in.wav out.wav [mix0-100]
// 补偿音频单元延迟（输出与输入逐样本对齐），尾部多渲染一段把延迟吐干净。
import AVFoundation

func fourCC(_ s: String) -> OSType { s.utf8.reduce(0) { ($0 << 8) | OSType($1) } }
let args = CommandLine.arguments
let inURL = URL(fileURLWithPath: args[1]), outURL = URL(fileURLWithPath: args[2])
let mix = args.count > 3 ? Float(args[3])! : 100
let file = try AVAudioFile(forReading: inURL)
let fmt = file.processingFormat
let engine = AVAudioEngine(), player = AVAudioPlayerNode()
let iso = AVAudioUnitEffect(audioComponentDescription: AudioComponentDescription(
  componentType: kAudioUnitType_Effect, componentSubType: fourCC("vois"), componentManufacturer: fourCC("appl"),
  componentFlags: 0, componentFlagsMask: 0))
engine.attach(player); engine.attach(iso)
engine.connect(player, to: iso, format: fmt)
engine.connect(iso, to: engine.mainMixerNode, format: fmt)
try engine.enableManualRenderingMode(.offline, format: fmt, maximumFrameCount: 4096)
for p in iso.auAudioUnit.parameterTree?.allParameters ?? [] {
  FileHandle.standardError.write("param \(p.address) \(p.identifier) '\(p.displayName)' [\(p.minValue),\(p.maxValue)] = \(p.value)\n".data(using: .utf8)!)
  if p.displayName.lowercased().contains("mix") { p.value = mix }
}
let lat = Int((iso.auAudioUnit.latency * fmt.sampleRate).rounded())
FileHandle.standardError.write("sr \(fmt.sampleRate) ch \(fmt.channelCount) latency \(iso.auAudioUnit.latency)s = \(lat) samples\n".data(using: .utf8)!)
try engine.start()
player.scheduleFile(file, at: nil); player.play()
let out = try AVAudioFile(forWriting: outURL, settings: [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: fmt.sampleRate,
  AVNumberOfChannelsKey: fmt.channelCount, AVLinearPCMBitDepthKey: 32, AVLinearPCMIsFloatKey: true], commonFormat: .pcmFormatFloat32, interleaved: false)
let buf = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: engine.manualRenderingMaximumFrameCount)!
let total = file.length + AVAudioFramePosition(lat)
var skip = lat
while engine.manualRenderingSampleTime < total {
  let n = AVAudioFrameCount(min(Int64(buf.frameCapacity), total - engine.manualRenderingSampleTime))
  guard try engine.renderOffline(n, to: buf) == .success else { break }
  if skip >= Int(buf.frameLength) { skip -= Int(buf.frameLength); continue }
  if skip > 0 {
    let keep = Int(buf.frameLength) - skip
    let t = AVAudioPCMBuffer(pcmFormat: buf.format, frameCapacity: AVAudioFrameCount(keep))!
    for c in 0..<Int(buf.format.channelCount) { memcpy(t.floatChannelData![c], buf.floatChannelData![c] + skip, keep * 4) }
    t.frameLength = AVAudioFrameCount(keep); try out.write(from: t); skip = 0
  } else { try out.write(from: buf) }
}
FileHandle.standardError.write("done frames in \(file.length)\n".data(using: .utf8)!)
