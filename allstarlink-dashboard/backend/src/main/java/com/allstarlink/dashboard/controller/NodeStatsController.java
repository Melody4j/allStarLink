package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.entity.Node;
import com.allstarlink.dashboard.service.NodeService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/stats")
@RequiredArgsConstructor
public class NodeStatsController {

    private final NodeService nodeService;

    // 获取全局统计信息
    @GetMapping("/global")
    public ResponseEntity<Map<String, Object>> getGlobalStats(
            @RequestParam(defaultValue = "1") int timeThresholdHours) {
        Map<String, Object> stats = nodeService.getGlobalStats(timeThresholdHours);
        return ResponseEntity.ok(stats);
    }

    // 获取所有在线节点详情（用于地图显示）
    @GetMapping("/location")
    public ResponseEntity<List<Node>> getNodeStatsByLocation() {
        // 返回所有在线节点的详细信息，而不是按位置分组
        List<Node> activeNodes = nodeService.getActiveNodes();
        return ResponseEntity.ok(activeNodes);
    }
}