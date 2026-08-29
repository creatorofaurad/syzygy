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

typedef enum {
    SYZYGY_MODE_PATROL = 0,
    SYZYGY_MODE_PHALANX = 1,
    SYZYGY_MODE_INTERCEPTOR_RINGS = 2,
    SYZYGY_MODE_EW_VORTEX = 3,
    SYZYGY_MODE_STRIKE_WAVE = 4,
    SYZYGY_MODE_COMMS_STEINER_TREE = 5,
    SYZYGY_MODE_APERTURE_RADAR = 6,
    SYZYGY_MODE_CRAM_INTERCEPT = 7,
    SYZYGY_MODE_AREA_DISPERSION = 8,
    SYZYGY_MODE_PINCER_ENVELOPE = 9,
    SYZYGY_MODE_GHOST_DECOY_MALD = 10,
    SYZYGY_MODE_NOE_TERRAIN_MASKING = 11,
    SYZYGY_MODE_TDOA_PASSIVE_GRID = 12,
    SYZYGY_MODE_STOT_SATURATION = 13,
    SYZYGY_MODE_CONVOY_ESCORT = 14,
    SYZYGY_MODE_FLAK_EVASION_JINK = 15
} SyzygyTacticalMode;

#pragma pack(push, 1)

// 64-byte aligned kinetic entity structure for AVX-512 & RV64GCV SIMD vectorization
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
    uint32_t current_tactical_mode;
    float average_step_latency_us;
} SyzygyTelemetry;

#pragma pack(pop)

// Initialize the deterministic lockless memory substrate arena
SYZYGY_API bool syzygy_init_substrate(uint8_t* ring_buffer_ptr, size_t buffer_size);

// Set real-time tactical formation mode (0-15)
SYZYGY_API bool syzygy_set_formation(uint8_t mode);

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
