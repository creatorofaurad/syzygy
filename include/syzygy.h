#ifndef SYZYGY_H
#define SYZYGY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * ============================================================================
 * PROJECT SYZYGY: Sovereign Bare-Metal Deterministic Coprocessor C-ABI Interface
 * ============================================================================
 */

typedef struct {
    float x, y, z;
    float vx, vy, vz;
    uint32_t flags;
    uint32_t entity_id;
} SyzygyKineticEntity;

typedef struct {
    uint64_t total_evaluations;
    uint64_t elapsed_nanoseconds;
    uint32_t active_jamming_zones;
    uint32_t collision_hazards_neutralized;
} SyzygyTelemetry;

// Initialize lockless ring memory arena
bool syzygy_init_substrate(uint8_t* ring_buffer_ptr, size_t buffer_size);

// Single-cycle AVX-512 SIMD swarm evaluation step (returns elapsed nanoseconds)
uint64_t syzygy_evaluate_swarm(SyzygyKineticEntity* entities, size_t count, float dt);

// Extract real-time telemetry from the deterministic coprocessor
bool syzygy_get_telemetry(SyzygyTelemetry* out_telemetry);

// Shut down coprocessor context cleanly
void syzygy_shutdown_substrate(void);

#ifdef __cplusplus
}
#endif

#endif // SYZYGY_H
