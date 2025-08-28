# 目前任务

## 完成app/logic下两个analyzer的合并
保证两个analyzer能够通过方便的统一形式调用。考虑把环境变量等共用信息提取出来。

## 建立一个前端页面
这个页面应有以下基本功能。

### 输入百炼API Key和拖入xlsx文件
用户输入Key和目标xlsx文件后，就自动用citation.py（待补充）进行分词，然后可以跑fulltext和sliced两个版本的analyze

### 显示结果JSON
跑出结果JSON后，应该可以在页面上方便地阅读这份JSON
