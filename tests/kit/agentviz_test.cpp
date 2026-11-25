// Native check of kit/scene/agentviz.h, run by tests/test_kit_native.py:
//   g++ -std=c++17 -I kit/scene tests/kit/agentviz_test.cpp -o agentviz_test
//   ./agentviz_test tests/kit/wire_fixture.f32 <string>...
// Prints JSON: the decoded fixture and fnv1a / seed_of for each string, so the
// Python side can compare them with agentfeed's seed_of and the packer's input.
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>

#include "agentviz.h"

namespace {

std::vector<float> readFloats(const char* path) {
    std::ifstream in(path, std::ios::binary);
    std::vector<char> bytes((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    std::vector<float> floats(bytes.size() / sizeof(float));
    std::copy(bytes.begin(), bytes.begin() + floats.size() * sizeof(float), reinterpret_cast<char*>(floats.data()));
    return floats;
}

void printAgent(const agentviz::Agent& a, bool last) {
    std::printf("{\"id\":%u,\"parent\":%u,\"kind\":%d,\"state\":%d,\"action\":%d,\"waitingReason\":%d,"
                "\"stalled\":%d,\"finished\":%d,\"seed\":%.6f,\"parentSeed\":%.6f,\"x\":%.6f,\"y\":%.6f,\"z\":%.6f,"
                "\"facing\":%.6f,\"appear\":%.6f,\"highlight\":%d,\"pulse\":%.6f,\"toolCount\":%d,"
                "\"activeFollowers\":%d,\"extra0\":%.6f,\"extra15\":%.6f}%s",
                a.id, a.parent, static_cast<int>(a.kind), static_cast<int>(a.state), static_cast<int>(a.action),
                static_cast<int>(a.waitingReason), a.stalled, a.finished, a.seed, a.parentSeed, a.x, a.y, a.z,
                a.facing, a.appear, static_cast<int>(a.highlight), a.pulse, a.toolCount, a.activeFollowers,
                a.extra[0], a.extra[15], last ? "" : ",");
}

void printFrame(const agentviz::Frame& f) {
    std::printf("\"frame\":{\"ok\":%s,\"waitingCount\":%d,\"fixture\":%d,\"scene0\":%.6f,\"scene15\":%.6f,",
                f.ok ? "true" : "false", f.waitingCount, f.fixture, f.scene[0], f.scene[15]);
    std::printf("\"zones\":[");
    for (size_t i = 0; i < f.zones.size(); ++i) {
        const auto& z = f.zones[i];
        std::printf("{\"id\":%u,\"kind\":%d,\"seed\":%.6f,\"x0\":%.6f,\"z1\":%.6f,\"appear\":%.6f,\"extra0\":%.6f}%s",
                    z.id, z.kind, z.seed, z.x0, z.z1, z.appear, z.extra[0], i + 1 < f.zones.size() ? "," : "");
    }
    std::printf("],\"agents\":[");
    for (size_t i = 0; i < f.agents.size(); ++i) printAgent(f.agents[i], i + 1 == f.agents.size());
    std::printf("],\"links\":[");
    for (size_t i = 0; i < f.links.size(); ++i) {
        const auto& l = f.links[i];
        std::printf("{\"kind\":%d,\"from\":%u,\"to\":%u,\"y1\":%.6f,\"alpha\":%.6f}%s", l.kind, l.from, l.to, l.y1,
                    l.alpha, i + 1 < f.links.size() ? "," : "");
    }
    std::printf("]}");
}

// A truncated buffer must be refused and leave the last good frame alone.
bool refusesTruncated(const std::vector<float>& data) {
    agentviz::Frame f;
    f.assign(data.data(), data.size());
    const size_t agents = f.agents.size();
    return !f.assign(data.data(), data.size() - 1) && !f.error.empty() && f.ok && f.agents.size() == agents;
}

// A header claiming far more records than the buffer holds must be refused
// before any allocation (on wasm32 the size arithmetic would otherwise wrap).
bool refusesHugeCounts() {
    std::vector<float> header(agentviz::kHeader, 0.0f);
    header[0] = agentviz::kMagic;
    header[1] = static_cast<float>(agentviz::kFormatVersion);
    header[3] = 1073741824.0f;  // 2^30 agents
    agentviz::Frame f;
    try {
        return !f.assign(header.data(), header.size()) && f.agents.empty();
    } catch (...) {
        return false;
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: agentviz_test <wire.f32> [string...]\n");
        return 2;
    }
    const std::vector<float> data = readFloats(argv[1]);
    agentviz::Frame frame;
    frame.assign(data.data(), data.size());
    std::printf("{");
    printFrame(frame);
    std::printf(",\"refusesTruncated\":%s,\"refusesHugeCounts\":%s,\"seeds\":[",
                refusesTruncated(data) ? "true" : "false", refusesHugeCounts() ? "true" : "false");
    for (int i = 2; i < argc; ++i) {
        std::printf("[%u,%.4f]%s", agentviz::fnv1a(argv[i]), agentviz::seed_of(argv[i]), i + 1 < argc ? "," : "");
    }
    std::printf("]}\n");
    return frame.ok ? 0 : 1;
}
