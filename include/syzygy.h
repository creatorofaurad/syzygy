#ifndef SYZYGY_H
#define SYZYGY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#if defined(_WIN32) || defined(__CYGWIN__)
    #if defined(SYZYGY_BUILD_DLL)
        #define SYZYGY_API __declspec(dllexport)
    #else
        #define SYZYGY_API __declspec(dllimport)
    #endif
#else
    #if defined(__GNUC__) && __GNUC__ >= 4
        #define SYZYGY_API __attribute__((visibility("default")))
    #else
        #define SYZYGY_API
    #endif
#endif

#ifdef __cplusplus
extern "C" {
#endif

/*
 * ============================================================================
 * PROJECT SYZYGY: Sovereign Bare-Metal Deterministic Coprocessor C-ABI Surface
 * Target: libsyzygy.a / libsyzygy.so / syzygy.dll
 * ============================================================================
 */

#pragma pack(push, 1)

// 64-byte aligned kinetic entity structure for AVX-512 vectorization
typedef struct {
    float x, y, z;
    float vx, vy, vz;
    float ax, ay, az;
    uint32_t flags;
    uint32_t entity_id;
    uint64_t timestamp_tsc;
    uint8_t reserved[16];
} SyzygyKineticEntity;

typedef struct {
    uint64_t total_evaluations;
    uint64_t elapsed_nanoseconds;
    uint32_t active_swarm_units;
    uint32_t collisions_neutralized;
    uint32_t ew_jamming_spheres;
    float average_step_latency_us;
} SyzygyTelemetry;

#pragma pack(pop)

// Initialize the deterministic lockless memory substrate arena
SYZYGY_API bool syzygy_init_substrate(uint8_t* ring_buffer_ptr, size_t buffer_size);

// Single-cycle AVX-512 SIMD swarm evaluation step (returns hardware TSC cycles)
SYZYGY_API uint64_t syzygy_evaluate_swarm(SyzygyKineticEntity* entities, size_t count, float dt);

// Extract real-time telemetry from the deterministic coprocessor
SYZYGY_API bool syzygy_get_telemetry(SyzygyTelemetry* out_telemetry);

// Read the invariant CPU core Time Stamp Counter (RDTSC)
SYZYGY_API uint64_t syzygy_read_tsc(void);

// Cleanly shut down the coprocessor memory arena
SYZYGY_API void syzygy_shutdown_substrate(void);

#ifdef __cplusplus
}
#endif

#endif // SYZYGY_H
