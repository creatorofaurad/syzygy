#[cfg(test)]
mod tests {
    use crate::arena::ConstraintGraphArena;
    use crate::ast::ConstraintType;
    use crate::proofs::ProofEmitter;
    use crate::rewriting::TermRewritingEngine;
    use crate::codegen::NativeCodegen;
    use crate::VerificationStatus;

    #[test]
    fn test_topological_graph_reduction_and_proof_emission() {
        let mut arena = ConstraintGraphArena::with_capacity(1024, 1024);
        
        let root = arena.alloc_node(ConstraintType::InvariantIdentity);
        let n1 = arena.alloc_node(ConstraintType::BoundedInterval { lower: 100, upper: 500 });
        let n2 = arena.alloc_node(ConstraintType::TemporalDeadline { max_ns: 5000 });

        arena.alloc_edge(root, n1, 1, false);
        arena.alloc_edge(root, n2, 1, false);

        let engine = TermRewritingEngine::new(100);
        let status = engine.reduce_to_normal_form(&mut arena, root);

        assert_eq!(status, VerificationStatus::VerifiedConfluent);
        assert!(arena.get_node(root).verified);

        let lean_proof = ProofEmitter::emit_lean4_proof(&arena, root);
        assert!(lean_proof.contains("theorem Syzygy_GraphConfluence"));
        assert!(lean_proof.contains("theorem Syzygy_ZeroHallucination_Bound"));

        let bytecode = NativeCodegen::emit_baremetal_bytecode(&arena, root);
        assert_eq!(&bytecode[0..4], &[0x53, 0x59, 0x5A, 0x59]);
        println!("\n✅ [SYZYGY TOPOLOGY] Verification Succeeded: Confluent normal form & Lean 4 Proof emitted!");
    }
}
