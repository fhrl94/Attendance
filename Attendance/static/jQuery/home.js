$(document).ready(function(){
    // 解决 jQuery post csrf中断 ，来源于 https://code.ziqiangxuetang.com/media/django/csrf.js
    jQuery(document).ajaxSend(function(event, xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        function sameOrigin(url) {
            // url could be relative or scheme relative or absolute
            var host = document.location.host; // host + port
            var protocol = document.location.protocol;
            var sr_origin = '//' + host;
            var origin = protocol + sr_origin;
            // Allow absolute or scheme relative URLs to same origin
            return (url === origin || url.slice(0, origin.length + 1) === origin + '/') ||
                (url === sr_origin || url.slice(0, sr_origin.length + 1) === sr_origin + '/') ||
                // or any other URL that isn't scheme relative or absolute i.e relative.
                !(/^(\/\/|http:|https:).*/.test(url));
        }
        function safeMethod(method) {
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }
        if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    });


    // 过滤异常
    function filter_attendance_info() {
        if ($('#content_filter').attr('checked')) {
            $(".check_status").each(function(){
                if($(this).text() === '否')
                    $(this).parent().addClass('hidden');
            });
        }
        else {
            $(".check_status").each(function(){
                if($(this).text() === '否')
                    $(this).parent().removeClass('hidden');
            });
        }
    }

    // 点击 过滤
    $('#content_filter').click(function () {
        if ($('#content_filter').attr('checked'))
            $("#content_filter").attr("checked", false);
        else
            $("#content_filter").attr("checked","checked");
        filter_attendance_info();
    });


    // 点击查询
    function query_init_once() {
        var today = new Date();
        $("#end_date").val(today.toISOString().substr(0, 10));
        today.setDate((today.getDate() - 31));
        $("#start_date").val(today.toISOString().substr(0, 10));
        $("#query_attendance").click();
    }


    $('#attendance_detail').click(function () {
       $('#criteria_title').text("考勤明细查询");
       title_type = 'attendance_detail';
       query_init_once()
    });

    $('#attendance_summary').click(function () {
       $('#criteria_title').text("考勤汇总查询");
       title_type = 'attendance_summary';
       query_init_once()
    });

    $('#edit_attendance').click(function () {
       $('#criteria_title').text("签卡明细查询");
       title_type = 'edit_attendance';
       query_init_once()
    });

    $('#leave_info').click(function () {
       $('#criteria_title').text("请假明细查询");
       title_type = 'leave_info';
       query_init_once()
    });

    $('#annual_leave_credits').click(function () {
       $('#criteria_title').text("假期额度查询");
       title_type = 'limit';
       query_init_once()
    });

    $('#help_text').click(function () {
       $('#criteria_title').text("常见问题说明");
       title_type = 'help_text';
       query_init_once()
    });

    // 查询请求
    $("#query_attendance").click(function(){
        var start_date = $("#start_date").val();
        var end_date = $("#end_date").val();
        var html_obj=$.ajax({url:"/Attendance/ajax_dict/",type: "POST",dataType:"json",
                data:{"start_date":start_date,"end_date":end_date, 'title_type':title_type}, async:false});
        var date_dict_list = JSON.parse( html_obj.responseText );
        if (date_dict_list.length) {
            if (date_dict_list[0]['err']) {
                $("#error_content").removeClass("hidden");
                $("#error_content").text(date_dict_list[0]['err']);
                $("#attendance_content").addClass("hidden");
                return
            }
        }
        $("#error_content").addClass("hidden");
        AttendanceInfo(date_dict_list);
      });

    // 数据展示
    function AttendanceInfo(date_dict_list) {
        $("#attendance_content").removeClass("hidden");
        $("#table_title").empty();
        var $title_tr_temp = $("<tr></tr>");
        $.each(content_dict[title_type], function () {
            $title_tr_temp.append("<th class=\"text-center\">" + this + "</th>");
        });
        $title_tr_temp.appendTo("#data_content_table");
        $title_tr_temp.appendTo("#table_title");
        $("#data_content_table").empty();
        for( var i = 0; i < date_dict_list.length; i++ ) {
            //动态创建一个tr行标签,并且转换成jQuery对象
            var $tr_temp = $("<tr></tr>");
            //往行里面追加 td单元格
            for(var key in content_dict[title_type]) {
                $tr_temp.append("<td class="+ key + ">" + date_dict_list[i][key] + "</td>");
            }
            $tr_temp.appendTo("#data_content_table");
        }
        $("#num_query").empty();
        $("#num_query").text("共查到 " + date_dict_list.length + " 条记录");
        switch (title_type){
            case 'attendance_detail':
                $('#content_filter_label').removeClass("hidden");
                $('#tips_attendance_detail').removeClass("hidden");
                $('#tips_attendance_summary').addClass("hidden");
                break;
            case 'attendance_summary':
                $('#tips_attendance_summary').removeClass("hidden");
                $('#tips_attendance_detail').addClass("hidden");
                $('#content_filter_label').addClass("hidden");break;
            default:
                $('#content_filter_label').addClass("hidden");
                $('#tips_attendance_detail').addClass("hidden");
                $('#tips_attendance_summary').addClass("hidden");
        }
        translate_data();
        filter_attendance_info();
    }

    // 初始化
    $(function () {
        $('#attendance_detail').click();
    });

    // 变量申明
    var title_type;
    var attendance_detail_title_dict = {'emp_id': '工号', 'attendance_date': '考勤日期', 'check_in':'上午打卡时间',
        'check_in_type_id': '上午出勤情况', 'check_in_status': '上午是否异常', 'check_out': '下午打卡时间',
        'check_out_type_id': '下午出勤情况', 'check_out_status': '下午是否异常', 'check_status': '全天是否有异常',
        'attendance_date_status': '是否工作日'};
    var attendance_summary_title_dict = {'emp_code': '工号', 'section_date': '汇总日期', 'arrive_total': '应到天数',
        'real_arrive_total': '实到天数', 'absenteeism_total': '旷工天数', 'late_total': '迟到/早退次数',
        'sick_leave_total': '病假天数', 'personal_leave_total': '事假天数', 'annual_leave_total': '年假天数',
        'marriage_leave_total': '婚假天数', 'bereavement_leave_total': '丧假天数',
        'paternity_leave_total': '陪产假天数', 'maternity_leave_total': '产假天数',
        'work_related_injury_leave_total': '工伤假天数', 'home_leave_total': '探亲假天数',
        'travelling_total': '出差天数' ,'other_leave_total': '其他假天数'};
    var edit_attendance_title_dict = {'emp_id': '工号', 'edit_attendance_date': '签卡日期',
        'edit_attendance_time_start':'上午签卡时间', 'edit_attendance_time_end': '下午签卡时间',
        'edit_attendance_type_id': '签卡原因', 'edit_attendance_status': '签卡单据状态',
        'edit_attendance_operate': '操作日期'};
    var leave_info_title_dict = {'emp_id': '工号', 'start_date': '开始日期',
        'leave_info_time_start':'开始请假时间',
        'end_date': '结束日期', 'leave_info_time_end': '结束请假时间', 'leave_type_id': '假期类型',
        'leave_info_status': '假期单据状态', 'leave_info_operate': '假期操作日期'};
    var limit_title_dict = {'emp_ins_id': '工号', 'holiday_type_id': '假期类型', 'rate': '周期', 'start_date': '开始日期',
        'end_date': '结束日期', 'standard_limit': '标准额度', 'standard_frequency': '标准次数', 'used_limit': '已用额度',
        'used_frequency': '已用次数', 'limit_edit': '额度增减', 'frequency_edit': '次数增减', 'surplus_limit': '剩余额度',
        'surplus_frequency': '剩余次数'
    };
    var content_dict = {'attendance_detail': attendance_detail_title_dict,
        'attendance_summary': attendance_summary_title_dict, 'edit_attendance': edit_attendance_title_dict,
        'leave_info': leave_info_title_dict, 'limit':limit_title_dict};

    // 翻译数据
    function translate_data() {
        // 全天是否有异常
        $(".check_in_status, .check_out_status").each(function(){
                switch ($(this).text()){
                    case '0': $(this).text("正常");break;
                    case '1': $(this).text("迟到");break;
                    case '2': $(this).text("早退");break;
                    case '3': $(this).text("旷工");break;
                }
            });
        // 全天是否异常
        $(".check_status").each(function(){
                switch ($(this).text()){
                    case 'false': $(this).text("否");break;
                    case 'true': $(this).text("异常");break;
                }
            });
        // 是否工作日
        $(".attendance_date_status").each(function(){
                switch ($(this).text()){
                    case 'false':
                        $(this).text("节假日");
                        $(this).parent().addClass("active");
                        break;
                    case 'true': $(this).text("工作日");break;
                }
            });
        // 时间为 null 替换为 ""
        $(".check_in, .check_out, .edit_attendance_time_start, .edit_attendance_time_end").each(function(){
                switch ($(this).text()){
                    case 'null': $(this).text("");break;
                }
            });
        // 请假、签卡单据状态
        $(".edit_attendance_status, .leave_info_status").each(function(){
                switch ($(this).text()){
                    case '0': $(this).text("未审核");break;
                    case '1': $(this).text("已审核");break;
                    case '2': $(this).text("已失效");break;
                }
            });
        // 请假、签卡单据原因
        $(".leave_type_id, .edit_attendance_type_id, .holiday_type_id").each(function(){
                switch ($(this).text()){
                    // case '1': $(this).text('打卡');break;
                    case '2': $(this).text('见客户');break;
                    case '3': $(this).text('参会');break;
                    case '4': $(this).text('因公外出');break;
                    case '5': $(this).text('查监控忘打卡');break;
                    case '6': $(this).text('查监控已打卡');break;
                    case '7': $(this).text('班车迟到');break;
                    case '8': $(this).text('特批');break;
                    case '9': $(this).text('出差');break;
                    case '10': $(this).text('其他');break;
                    case '11': $(this).text('事假');break;
                    case '12': $(this).text('病假');break;
                    case '13': $(this).text('年假');break;
                    case '14': $(this).text('婚假');break;
                    case '15': $(this).text('丧假');break;
                    case '16': $(this).text('产假');break;
                    case '17': $(this).text('陪产假');break;
                    case '18': $(this).text('出差（请假）');break;
                    case '19': $(this).text('其他假');break;
                    case '20': $(this).text('工伤假');break;
                    case '21': $(this).text('探亲假');break;
                }
            });
        // 出勤状况
        $(".check_in_type_id, .check_out_type_id").each(function(){
                switch ($(this).text()){
                    case '打卡': break;
                    case '未打卡': break;
                    case '见客户': break;
                    case '参会': break;
                    case '因公外出': break;
                    case '查监控忘打卡': break;
                    case '查监控已打卡': break;
                    case '班车迟到': break;
                    case '特批': break;
                    case '出差': break;
                    case '其他': break;
                    default:
                        $(this).prev().text("")
                }
            });
        // 周期
        $(".rate").each(function () {
            switch ($(this).text()) {
                case '0': $(this).text('年');break;
                case '1': $(this).text('月');break;
                default:
                        $(this).text('');
            }
        })
    }
});
