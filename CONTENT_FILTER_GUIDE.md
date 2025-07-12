# 内容过滤器使用指南

## 📖 概述

内容过滤器是网站爬虫的一个重要功能，它可以帮助您自动过滤掉页面中不需要的内容，如页脚、广告、导航栏等，让抓取的内容更加干净和有价值。

## 🚀 功能特点

- **预设过滤器**：提供8种常用的预设过滤规则
- **自定义选择器**：支持自定义CSS选择器进行精确过滤
- **关键词过滤**：基于关键词自动识别和过滤不需要的内容
- **智能识别**：自动识别页脚、广告、弹窗等常见元素
- **统计报告**：提供详细的过滤统计信息

## 🎯 预设过滤器

### 1. 页脚 (footer)
- **说明**：过滤页面底部的版权信息、联系方式等
- **适用场景**：几乎所有网站
- **CSS选择器**：`footer`, `.footer`, `#footer`, `.site-footer` 等
- **关键词**：版权所有, ©, copyright, 联系我们, 友情链接

### 2. 页头 (header)
- **说明**：过滤页面顶部的头部信息
- **适用场景**：当您只需要主要内容时
- **CSS选择器**：`header`, `.header`, `#header`, `.site-header` 等

### 3. 导航栏 (navigation)
- **说明**：过滤导航菜单和面包屑
- **适用场景**：专注于正文内容的抓取
- **CSS选择器**：`nav`, `.nav`, `.navigation`, `.navbar`, `.menu` 等

### 4. 广告 (ads)
- **说明**：过滤各种广告内容
- **适用场景**：所有商业网站
- **CSS选择器**：`.ad`, `.ads`, `.advertisement`, `.banner` 等
- **关键词**：广告, 推广, AD, ads, advertisement, sponsored

### 5. 社交媒体 (social)
- **说明**：过滤社交媒体分享按钮和链接
- **适用场景**：内容分析和存储
- **CSS选择器**：`.social`, `.social-media`, `.share-buttons` 等
- **关键词**：分享, 关注我们, follow us, share

### 6. 评论区 (comments)
- **说明**：过滤用户评论和讨论区
- **适用场景**：只需要原创内容时
- **CSS选择器**：`.comments`, `.comment`, `#disqus_thread` 等
- **关键词**：评论, 留言, comments, discussion

### 7. 侧边栏 (sidebar)
- **说明**：过滤侧边栏小工具和次要内容
- **适用场景**：专注于主要内容的抓取
- **CSS选择器**：`.sidebar`, `.widget`, `.aside` 等

### 8. 弹窗 (popup)
- **说明**：过滤弹出窗口和模态框
- **适用场景**：所有网站
- **CSS选择器**：`.popup`, `.modal`, `.overlay`, `.lightbox` 等

## 🛠️ 使用方法

### Web界面使用

1. **启用预设过滤器**
   ```
   在"内容过滤"部分，勾选需要的预设过滤器：
   ☑️ 页脚
   ☑️ 广告  
   ☑️ 弹窗
   ☐ 导航栏
   ☐ 侧边栏
   ```

2. **自定义CSS选择器**
   ```
   在"自定义CSS选择器"框中输入：
   .advertisement, #popup, .sidebar, .related-posts
   ```

3. **自定义关键词**
   ```
   在"自定义关键词"框中输入：
   广告, 推广, 赞助, 相关推荐
   ```

### 编程接口使用

```python
from content_filter import ContentFilter

# 创建过滤器
content_filter = ContentFilter(
    enabled_filters=['footer', 'ads', 'popup'],
    custom_selectors=['.advertisement', '#sidebar'],
    custom_keywords=['广告', '推广']
)

# 过滤HTML内容
filtered_html = content_filter.filter_html(html_content)

# 过滤文本内容
filtered_text = content_filter.filter_text(text_content)

# 获取统计信息
stats = content_filter.get_filter_stats()
```

## 📊 配置建议

### 通用网站
```
推荐配置：
- 启用：footer, ads, popup
- 自定义选择器：.related, .recommended
- 自定义关键词：广告, 推广
```

### 新闻网站
```
推荐配置：
- 启用：footer, ads, comments, social
- 自定义选择器：.breaking-news-bar, .newsletter
- 自定义关键词：订阅, 推送, 热门推荐
```

### 技术文档
```
推荐配置：
- 启用：footer, ads
- 保留：navigation（有助于理解文档结构）
- 自定义选择器：.version-selector, .edit-page
```

### 电商网站
```
推荐配置：
- 启用：footer, ads, social, sidebar
- 自定义选择器：.price-comparison, .related-products
- 自定义关键词：促销, 限时优惠, 立即购买
```

## 🔧 高级配置

### 精确控制
```python
# 只过滤特定类型的广告
content_filter = ContentFilter(
    custom_selectors=[
        '.google-ad',
        '.adsense',
        '[class*="ad-"]',
        '[id*="advertisement"]'
    ]
)

# 基于内容长度的智能过滤
content_filter = ContentFilter(
    custom_keywords=['版权所有', '联系我们'],
    # 过滤器会自动判断包含关键词的短文本
)
```

### 条件过滤
```python
# 根据网站类型动态配置
def create_filter_for_site(site_type):
    if site_type == 'news':
        return ContentFilter(['footer', 'ads', 'comments'])
    elif site_type == 'docs':
        return ContentFilter(['footer', 'ads'])
    else:
        return ContentFilter(['footer', 'ads', 'popup'])
```

## 📈 效果示例

### 过滤前
```html
<html>
<body>
    <header>网站导航</header>
    <main>
        <h1>重要内容</h1>
        <p>这是有价值的内容...</p>
    </main>
    <aside class="sidebar">侧边栏广告</aside>
    <footer>版权所有 © 2025</footer>
    <div class="popup">弹窗广告</div>
</body>
</html>
```

### 过滤后（启用footer, ads, popup）
```html
<html>
<body>
    <header>网站导航</header>
    <main>
        <h1>重要内容</h1>
        <p>这是有价值的内容...</p>
    </main>
    <aside class="sidebar">侧边栏广告</aside>
</body>
</html>
```

## ⚠️ 注意事项

1. **谨慎使用导航过滤**：导航信息可能包含重要的网站结构信息
2. **测试过滤效果**：建议先在小范围测试过滤配置
3. **备份原始内容**：过滤是不可逆的，建议保留原始内容
4. **定期调整配置**：不同网站可能需要不同的过滤策略

## 🧪 测试工具

运行测试脚本查看过滤效果：

```bash
python test_content_filter.py
```

这将展示不同过滤配置的效果对比，帮助您选择最适合的配置。

## 🔍 故障排除

### 过滤效果不理想
1. 检查CSS选择器是否正确
2. 尝试添加更多的自定义选择器
3. 使用浏览器开发者工具检查页面结构

### 重要内容被误过滤
1. 减少启用的预设过滤器
2. 检查自定义关键词是否过于宽泛
3. 使用更精确的CSS选择器

### 过滤速度较慢
1. 减少自定义选择器数量
2. 优化CSS选择器的复杂度
3. 考虑只启用必要的过滤器

## 📚 更多资源

- [CSS选择器参考](https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Selectors)
- [BeautifulSoup文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [网页抓取最佳实践](./README.md)

---

通过合理配置内容过滤器，您可以获得更加干净、有价值的网页内容，提高数据质量和分析效率。 