# Mermaid Examples

Use this file when code snippets are useful for selecting syntax or copying a starting point.

## Basic Flow

```mermaid
graph TD
    A[Start] --> B[Process 1]
    B --> C{Decision}
    C -->|Yes| D[Process 2]
    C -->|No| E[Process 3]
    D --> F[End]
    E --> F
```

## Horizontal Code Call Graph

```mermaid
graph LR
    ocf_read_fast --> ocf_req_get["增加引用计数 (*ocf_req_get*)"]
    ocf_read_fast --> ocf_req_hash["计算哈希值 (*ocf_req_hash*)"]
    ocf_read_fast --> ocf_hb_req_prot_lock_rd["获取哈希桶读锁 (*ocf_hb_req_prot_lock_rd*)"]
    ocf_read_fast --> ocf_engine_traverse["遍历检查缓存行 (*ocf_engine_traverse*)"]
    ocf_read_fast --> ocf_engine_is_hit["检查命中状态 (*ocf_engine_is_hit*)"]
    ocf_read_fast --> ocf_user_part_has_space["检查分区空间 (*ocf_user_part_has_space*)"]
    ocf_read_fast --> ocf_io_start["启动 IO 操作 (*ocf_io_start*)"]
    ocf_read_fast --> ocf_req_async_lock_rd["异步获取缓存行读锁 (*ocf_req_async_lock_rd*)"]
    ocf_read_fast --> ocf_hb_req_prot_unlock_rd["释放哈希桶读锁 (*ocf_hb_req_prot_unlock_rd*)"]
    ocf_read_fast --> _ocf_read_fast_do["执行快速读取 (*_ocf_read_fast_do*)"]
    ocf_read_fast --> ocf_req_put["减少引用计数 (*ocf_req_put*)"]

    _ocf_read_fast_do --> ocf_engine_is_miss["检查是否未命中 (*ocf_engine_is_miss*)"]
    _ocf_read_fast_do --> ocf_read_pt_do["切换到直通模式 (*ocf_read_pt_do*)"]
    _ocf_read_fast_do --> ocf_engine_needs_repart["检查重分区需求 (*ocf_engine_needs_repart*)"]
    _ocf_read_fast_do --> ocf_hb_req_prot_lock_wr["获取哈希桶写锁 (*ocf_hb_req_prot_lock_wr*)"]
    _ocf_read_fast_do --> ocf_user_part_move["移动分区 (*ocf_user_part_move*)"]
    _ocf_read_fast_do --> ocf_hb_req_prot_unlock_wr["释放哈希桶写锁 (*ocf_hb_req_prot_unlock_wr*)"]
    _ocf_read_fast_do --> ocf_submit_cache_reqs["提交缓存请求 (*ocf_submit_cache_reqs*)"]
    _ocf_read_fast_do --> ocf_req_put["减少引用计数 (*ocf_req_put*)"]

    ocf_submit_cache_reqs --> _ocf_read_fast_complete["读取完成回调 (*_ocf_read_fast_complete*)"]
    _ocf_read_fast_complete --> ocf_req_put["减少引用计数 (*ocf_req_put*)"]
    ocf_engine_on_resume --> _ocf_read_fast_do["恢复执行读取 (*_ocf_read_fast_do*)"]
```

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> A
    A --> B
    B --> C
    C --> C: Repeat until complete.
    C --> B: Dynamic diagram update.
    C --> [*]

    A: User Request
    B: LLM breaks request into sub tasks with Mermaid diagram.
    C: LLM interprets Mermaid diagram step by step.
```

## Sequence Diagram

```mermaid
sequenceDiagram
    Alice ->> Bob: Hello Bob, how are you?
    Bob -->> John: How about you John?
    Bob --x Alice: I am good thanks.
    Bob -x John: I am good thanks.
    Note right of John: Bob waits for John before replying.
    Bob --> Alice: Checking with John.
    Alice ->> John: John, how are you?
```

## Class Diagram

```mermaid
---
title: Animal example
---
classDiagram
    note "From Duck to Zebra"
    Animal <|-- Duck
    note for Duck "can fly\ncan swim\ncan dive\ncan help in debugging"
    Animal <|-- Fish
    Animal <|-- Zebra
    Animal : +int age
    Animal : +String gender
    Animal : +isMammal()
    Animal : +mate()
    class Duck{
        +String beakColor
        +swim()
        +quack()
    }
    class Fish{
        -int sizeInFeet
        -canEat()
    }
    class Zebra{
        +bool is_wild
        +run()
    }
```
