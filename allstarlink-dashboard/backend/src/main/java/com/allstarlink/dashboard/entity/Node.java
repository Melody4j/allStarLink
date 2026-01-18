package com.allstarlink.dashboard.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.*;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
@TableName("node")
public class Node {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    
    @TableField("node_id")
    private Integer nodeId;
    
    private String owner;
    private String callsign;
    private String frequency;
    private String tone;
    private String location;
    private String site;
    private String affiliation;
    
    @TableField("last_seen")
    private LocalDateTime lastSeen;
    
    private String features;
    
    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    
    @TableField("is_active")
    private Boolean isActive;
    
    private Double latitude;
    private Double longitude;
}