//初始化ace编辑器对象
editor = ace.edit("sql_content_editor");

//设置风格和语言（更多风格和语言，请到github上相应目录查看）
theme = "textmate";
language = "sql";
editor.setTheme("ace/theme/" + theme);
editor.session.setMode("ace/mode/" + language);
editor.$blockScrolling = Infinity;
editor.setValue("");

//字体大小
editor.setFontSize(12);

//设置只读（true时只读，用于展示代码）
editor.setReadOnly(false);

//自动换行,设置为off关闭
editor.setOption("wrap", "free");
editor.getSession().setUseWrapMode(true);

//启用提示菜单
ace.require("ace/ext/language_tools");
editor.setOptions({
    enableBasicAutocompletion: true,
    enableSnippets: true,
    enableLiveAutocompletion: true
});

//绑定快捷键
editor.commands.addCommand({
    name: "alter",
    bindKey: {win: "Ctrl-Enter", mac: "Command-Enter"},
    exec: function (editor) {
        alert(editor.getValue())
    }
});

//设置自动提示代码
var setCompleteData = function (data) {
    var langTools = ace.require("ace/ext/language_tools");
    langTools.addCompleter({
        getCompletions: function (editor, session, pos, prefix, callback) {
            if (prefix.length === 0) {
                return callback(null, []);
            } else {
                return callback(null, data);
            }
        }
    });
};
