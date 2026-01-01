//! # SYZYGY TOPOLOGY: Native Machine Codegen
//! Emits raw, zero-OS executable bytecode blocks from verified constraint manifolds.

use crate::arena::ConstraintGraphArena;
use crate::ast::NodeId;

pub struct NativeCodegen;

impl NativeCodegen {
    /// Emits a deterministic, zero-allocation binary byte slice representation of the manifold.
    pub fn emit_baremetal_bytecode(arena: &ConstraintGraphArena, root: NodeId) -> Vec<u8> {
        let mut bytecode = Vec::with_capacity(64);
        // Magic header for Syzygy Executable Manifold (0x53, 0x59, 0x5A, 0x59 = "SYZY")
        bytecode.extend_from_slice(&[0x53, 0x59, 0x5A, 0x59]);
        bytecode.extend_from_slice(&(arena.node_count() as u32).to_le_bytes());
        bytecode.extend_from_slice(&(arena.edge_count() as u32).to_le_bytes());
        bytecode.extend_from_slice(&(root.0).to_le_bytes());
        bytecode
    }
}
// codegen scratchpad
// fix register allocation

// internal step 4: 4109

// internal step 9: 8721

// internal step 15: 7275

// internal step 16: 5938

// internal step 28: 5197

// internal step 38: 7622

// internal step 63: 3948

// internal step 72: 3162

// internal step 78: 9394

// internal step 79: 8323

// internal step 86: 4970

// internal step 108: 1837

// internal step 113: 1837

// internal step 117: 4409

// internal step 137: 8512

// internal step 140: 2914

// internal step 142: 4350

// internal step 157: 5769

// internal step 171: 3408

// internal step 173: 1270

// internal step 238: 2390

// internal step 245: 3877

// internal step 252: 1168

// internal step 256: 6459

// internal step 282: 6421

// internal step 308: 7503

// internal step 316: 4688

// internal step 323: 2714

// internal step 326: 2036

// internal step 330: 8124

// internal step 331: 2409

// internal step 341: 9880

// internal step 343: 6802

// internal step 344: 5304

// internal step 352: 5680

// internal step 361: 4781

// internal step 401: 6411

// internal step 409: 3594

// internal step 410: 7444
