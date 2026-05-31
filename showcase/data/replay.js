window.REPLAY = {
  run: {
    scores: {
      fold_reward: 0,
      health_score: 0,
      hydrophobic_contacts: 0
    }
  },
  episodes: [
    { id: "sample-episode", score: 0, status: "sample" }
  ],
  replay: {
    "sample-episode": [
      {
        observation: {
          task: "Fold the protein on a 2D lattice without collisions. Choose direction and mutation.",
          scenario: "Sample CFTR-like chloride channel segment",
          risk_notes: "Export a Mesocosm run to replace this sample replay.",
          step: 0,
          max_steps: 15,
          sequence: "HPPHCHPHHPPCHHP",
          placed_count: 1,
          next_residue: { index: 1, class: "P", label: "polar", is_critical: false },
          chain: [{ index: 0, class: "H", original_class: "H", label: "hydrophobic", x: 0, y: 0, critical: false }],
          valid_directions: ["up", "right", "down", "left"],
          score_so_far: 0,
          health_burden: 0,
          message: "Sample replay. Run Mesocosm export to see model turns."
        },
        reasoning: "Sample placeholder reasoning.",
        action: { direction: "right", mutation: "keep" },
        reward: 0,
        terminated: false,
        truncated: false,
        info: {
          fold_state: "{\"scenario_id\":\"sample\",\"scenario_name\":\"Sample CFTR-like chloride channel segment\",\"sequence\":\"HPPHCHPHHPPCHHP\",\"chain\":[{\"index\":0,\"class\":\"H\",\"original_class\":\"H\",\"label\":\"hydrophobic\",\"x\":0,\"y\":0,\"critical\":false}],\"grid_limit\":6,\"critical_indices\":[4,11,14],\"mutations\":[],\"contacts\":0,\"exposed_hydrophobics\":1,\"compactness\":1,\"health_burden\":0,\"health_score\":1,\"total_reward\":0,\"event\":\"sample\",\"status\":\"sample\"}",
          action_detail: "{\"direction\":\"right\",\"mutation\":\"keep\"}",
          event: "sample",
          status: "sample",
          score: "0",
          turn_reward: "0",
          health_burden: "0",
          health_score: "1",
          contacts: "0"
        }
      }
    ]
  }
};
