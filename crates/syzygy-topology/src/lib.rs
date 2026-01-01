//! # SYZYGY TOPOLOGY
//! Neuro-Symbolic Topological Compiler & Category-Theoretic Manifold Engine.

pub mod ast;
pub mod category;
pub mod rewriting;
pub mod proofs;
pub mod arena;
pub mod codegen;

#[cfg(test)]
mod tests;

/// Core Invariant Verification State
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerificationStatus {
    VerifiedConfluent,
    VerificationFailed,
    TopologicalSingularity,
}
