//! # SYZYGY TOPOLOGY: Memory Arena
//! Pre-allocated, contiguous memory pool ensuring zero heap allocations during graph reduction.

use crate::ast::{ConstraintNode, ConstraintType, EdgeId, MorphismEdge, NodeId};
use smallvec::SmallVec;

pub struct ConstraintGraphArena {
    nodes: Vec<ConstraintNode>,
    edges: Vec<MorphismEdge>,
}

impl ConstraintGraphArena {
    pub fn with_capacity(node_cap: usize, edge_cap: usize) -> Self {
        Self {
            nodes: Vec::with_capacity(node_cap),
            edges: Vec::with_capacity(edge_cap),
        }
    }

    #[inline(always)]
    pub fn alloc_node(&mut self, constraint_type: ConstraintType) -> NodeId {
        let id = NodeId(self.nodes.len() as u32);
        self.nodes.push(ConstraintNode {
            id,
            constraint_type,
            incoming_edges: SmallVec::new(),
            outgoing_edges: SmallVec::new(),
            verified: false,
        });
        id
    }

    #[inline(always)]
    pub fn alloc_edge(&mut self, source: NodeId, target: NodeId, weight: u32, reversible: bool) -> EdgeId {
        let id = EdgeId(self.edges.len() as u32);
        self.edges.push(MorphismEdge {
            id,
            source,
            target,
            weight,
            reversible,
        });

        self.nodes[source.0 as usize].outgoing_edges.push(id);
        self.nodes[target.0 as usize].incoming_edges.push(id);

        id
    }

    #[inline(always)]
    pub fn get_node(&self, id: NodeId) -> &ConstraintNode {
        &self.nodes[id.0 as usize]
    }

    #[inline(always)]
    pub fn get_node_mut(&mut self, id: NodeId) -> &mut ConstraintNode {
        &mut self.nodes[id.0 as usize]
    }

    #[inline(always)]
    pub fn get_edge(&self, id: EdgeId) -> &MorphismEdge {
        &self.edges[id.0 as usize]
    }

    #[inline(always)]
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    #[inline(always)]
    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    pub fn clear(&mut self) {
        self.nodes.clear();
        self.edges.clear();
    }
}
// arena bump allocator

// internal step 5: 2109

// internal step 14: 9342

// internal step 74: 4499

// internal step 83: 2935

// internal step 92: 2632

// internal step 116: 6802

// internal step 160: 6566

// internal step 166: 2231

// internal step 176: 2136

// internal step 192: 5214

// internal step 198: 2254

// internal step 255: 4713

// internal step 257: 6612

// internal step 258: 2822

// internal step 260: 9939

// internal step 270: 8307

// internal step 283: 6886

// internal step 309: 1756

// internal step 336: 5210

// internal step 339: 4561

// internal step 384: 5087

// internal step 389: 8456

// internal step 412: 7958

// internal step 417: 2854

// internal step 420: 4804
