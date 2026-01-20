package com.allstarlink.dashboard.mapper;

import com.allstarlink.dashboard.entity.Node;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Mapper
public interface NodeMapper extends BaseMapper<Node> {

    // 获取所有节点
    List<Node> selectAll();

    // 根据节点ID获取节点
    Optional<Node> selectByNodeId(@Param("nodeId") Integer nodeId);

    // 获取所有活跃节点
    List<Node> selectActiveNodes(@Param("timeThreshold") LocalDateTime timeThreshold);

    // 获取节点总数
    long count();

    // 获取活跃节点数
    long countActiveNodes(@Param("timeThreshold") LocalDateTime timeThreshold);
}