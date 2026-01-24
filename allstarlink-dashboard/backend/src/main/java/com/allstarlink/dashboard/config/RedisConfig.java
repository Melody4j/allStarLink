package com.allstarlink.dashboard.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * Redis配置类
 * 配置Redis缓存策略和序列化方式
 */
@Configuration
@EnableCaching
@Slf4j
public class RedisConfig {

    /**
     * 配置RedisTemplate
     * 设置键值序列化方式
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        // 使用Jackson2JsonRedisSerializer来序列化和反序列化redis的value值
        Jackson2JsonRedisSerializer<Object> jackson2JsonRedisSerializer = createJacksonSerializer();

        StringRedisSerializer stringRedisSerializer = new StringRedisSerializer();

        // key采用String的序列化方式
        template.setKeySerializer(stringRedisSerializer);
        // hash的key也采用String的序列化方式
        template.setHashKeySerializer(stringRedisSerializer);
        // value序列化方式采用jackson
        template.setValueSerializer(jackson2JsonRedisSerializer);
        // hash的value序列化方式采用jackson
        template.setHashValueSerializer(jackson2JsonRedisSerializer);
        template.afterPropertiesSet();

        return template;
    }

    /**
     * 配置缓存管理器
     * 为不同的缓存设置不同的过期时间
     */
    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        // 配置序列化
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(1))  // 默认缓存1分钟
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(createJacksonSerializer()))
                .disableCachingNullValues();

        // 为不同的缓存设置不同的过期时间
        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();

        // 节点列表缓存 - 2分钟过期
        cacheConfigurations.put("allNodes", config.entryTtl(Duration.ofMinutes(2)));

        // 活跃节点缓存 - 1分钟过期
        cacheConfigurations.put("activeNodes", config.entryTtl(Duration.ofMinutes(1)));

        // 全局统计缓存 - 30秒过期
        cacheConfigurations.put("globalStats", config.entryTtl(Duration.ofSeconds(30)));

        // 分页节点缓存 - 1分钟过期
        cacheConfigurations.put("nodesByPage", config.entryTtl(Duration.ofMinutes(1)));

        // 单个节点缓存 - 5分钟过期
        cacheConfigurations.put("nodeById", config.entryTtl(Duration.ofMinutes(5)));

        // 限定活跃节点缓存 - 1分钟过期
        cacheConfigurations.put("limitedActiveNodes", config.entryTtl(Duration.ofMinutes(1)));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(config)
                .withInitialCacheConfigurations(cacheConfigurations)
                .build();
    }

    /**
     * 创建Jackson序列化器
     * 使用简化配置避免LocalDateTime序列化问题
     */
    private Jackson2JsonRedisSerializer<Object> createJacksonSerializer() {
        Jackson2JsonRedisSerializer<Object> serializer = new Jackson2JsonRedisSerializer<>(Object.class);

        ObjectMapper objectMapper = new ObjectMapper();

        // 注册Java 8时间模块
        objectMapper.findAndRegisterModules();

        // 配置时间格式为字符串而非时间戳
        objectMapper.disable(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

        // 忽略未知属性，避免反序列化失败
        objectMapper.configure(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        // 设置可见性
        objectMapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);

        // 不使用类型信息，避免序列化复杂性
        // objectMapper.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.PROPERTY);

        serializer.setObjectMapper(objectMapper);
        return serializer;
    }
}