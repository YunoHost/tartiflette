
function daysAgo(timestamp) {
    var difference = Math.round(+new Date()/1000) - timestamp;
    var daysDifference = Math.round(difference/60/60/24);
    //return (new Date(timestamp*1000));
    return "(" + daysDifference + " days ago)";
}

$(".daysAgo").each(function () {
    var t = $(this).attr("timestamp");
    var console = $(this).attr("console");
    if (t) { 
        link = document.createElement('a');
        link.setAttribute('href', console);
        link.innerHTML = daysAgo(t);
        this.appendChild(link);
    }
    //    $(this).text(daysAgo(t)); 
    //}
});

$(".ci-app-test-result div[value=True]").addClass("success")
$(".ci-app-test-result div[value=False]").addClass("danger")
