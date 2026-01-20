package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.entity.Node;
import com.allstarlink.dashboard.service.NodeService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/nodes")
@RequiredArgsConstructor
public class NodeController {

    private final NodeService nodeService;

    // 获取所有节点
    @GetMapping
    public ResponseEntity<List<Node>> getAllNodes() {
        List<Node> nodes = nodeService.getAllNodes();
        return ResponseEntity.ok(nodes);
    }
    
    // 分页获取节点
    @GetMapping("/page")
    public ResponseEntity<Map<String, Object>> getNodesByPage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "20") int pageSize) {
        Map<String, Object> result = nodeService.getNodesByPage(pageNum, pageSize);
        return ResponseEntity.ok(result);
    }

    // 根据节点ID获取节点
    @GetMapping("/{nodeId}")
    public ResponseEntity<Node> getNodeById(@PathVariable Integer nodeId) {
        Optional<Node> node = nodeService.getNodeById(nodeId);
        return node.map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
    }

    // 获取所有活跃节点
    @GetMapping("/active")
    public ResponseEntity<List<Node>> getActiveNodes() {
        List<Node> nodes = nodeService.getActiveNodes();
        return ResponseEntity.ok(nodes);
    }


}