//! # SYZYGY TOPOLOGY: Constraint Graph Abstract Syntax Tree
//! High-performance, zero-allocation AST representing topological constraint manifolds.

use smallvec::SmallVec;

/// Strongly typed identifier referencing a node inside the memory arena.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(transparent)]
pub struct NodeId(pub u32);

/// Strongly typed identifier referencing an edge morphism inside the memory arena.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(transparent)]
pub struct EdgeId(pub u32);

/// Type descriptor of a topological constraint manifold
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstraintType {
    /// Strict equality invariant: A ≡ B
    InvariantIdentity,
    /// Bounded continuous interval: lower <= X <= upper (encoded in fixed-point 1e8)
    BoundedInterval { lower: i64, upper: i64 },
    /// Topological path equivalence in Homotopy Type Theory
    HomotopyPath,
    /// Non-cooperative game-theoretic Nash utility constraint
    NashEquilibrium { min_utility: u32 },
    /// Mission-critical hard temporal deadline (nanoseconds)
    TemporalDeadline { max_ns: u64 },
}

/// A node in the topological constraint graph representing an atomic proposition or physical state.
#[derive(Debug, Clone)]
pub struct ConstraintNode {
    pub id: NodeId,
    pub constraint_type: ConstraintType,
    pub incoming_edges: SmallVec<[EdgeId; 4]>,
    pub outgoing_edges: SmallVec<[EdgeId; 4]>,
    pub verified: bool,
}

/// A directed morphism (arrow) between two constraint nodes representing a reduction rule or inference.
#[derive(Debug, Clone)]
pub struct MorphismEdge {
    pub id: EdgeId,
    pub source: NodeId,
    pub target: NodeId,
    pub weight: u32,
    pub reversible: bool,
}
// syntax tree scratchpad

// internal step 19: 9588

// internal step 21: 3498

// internal step 22: 9700

// internal step 27: 6236

// internal step 51: 9965

// internal step 66: 5023

// internal step 67: 2618

// internal step 71: 3739

// internal step 80: 5245

// internal step 98: 1721

// internal step 102: 9676

// internal step 114: 2605

// internal step 130: 7856

// internal step 136: 1459

// internal step 138: 9327

// internal step 143: 6797

// internal step 145: 1201

// internal step 154: 1044

// internal step 162: 4212

// internal step 167: 6216

// internal step 169: 2894

// internal step 185: 7364

// internal step 191: 5044

// internal step 196: 8349

// internal step 208: 4602

// internal step 213: 7282

// internal step 235: 1897

// internal step 236: 5937

// internal step 248: 9094

// internal step 264: 2581

// internal step 265: 1049

// internal step 268: 4304

// internal step 299: 5371

// internal step 303: 4081

// internal step 325: 9832

// internal step 360: 4500

// internal step 379: 7882

// internal step 393: 5148

// internal step 395: 5646

// internal step 397: 2071

// internal step 405: 5429
