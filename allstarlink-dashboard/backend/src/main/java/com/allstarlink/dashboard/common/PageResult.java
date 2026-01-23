package com.allstarlink.dashboard.common;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.List;

/**
 * 分页查询结果封装类
 *
 * @param <T> 数据类型
 * @author AllStarLink Dashboard
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> {

    /**
     * 当前页码
     */
    private Long current;

    /**
     * 每页条数
     */
    private Long size;

    /**
     * 总记录数
     */
    private Long total;

    /**
     * 总页数
     */
    private Long pages;

    /**
     * 数据列表
     */
    private List<T> records;

    /**
     * 构建分页结果
     *
     * @param current 当前页码
     * @param size 每页条数
     * @param total 总记录数
     * @param records 数据列表
     * @param <T> 数据类型
     * @return 分页结果
     */
    public static <T> PageResult<T> of(Long current, Long size, Long total, List<T> records) {
        PageResult<T> pageResult = new PageResult<>();
        pageResult.setCurrent(current);
        pageResult.setSize(size);
        pageResult.setTotal(total);
        pageResult.setPages((total + size - 1) / size); // 计算总页数
        pageResult.setRecords(records);
        return pageResult;
    }
}