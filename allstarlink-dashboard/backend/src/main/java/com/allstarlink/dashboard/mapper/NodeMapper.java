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

    // 根据位置查询节点
    List<Node> selectByLocationContaining(@Param("location") String location);

    // 获取按位置分组的节点统计
    List<Map<String, Object>> selectNodeStatsByLocation(@Param("timeThreshold") LocalDateTime timeThreshold);



    // 根据地理范围查询节点
    List<Node> selectNodesByGeoBounds(@Param("minLat") double minLat, @Param("maxLat") double maxLat,
                                     @Param("minLon") double minLon, @Param("maxLon") double maxLon);

    // 获取节点总数
    long count();

    // 获取活跃节点数
    long countActiveNodes(@Param("timeThreshold") LocalDateTime timeThreshold);
}