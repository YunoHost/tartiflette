
function daysAgo(timestamp) {
    var difference = Math.round(+new Date()/1000) - timestamp;
    var daysDifference = Math.round(difference/60/60/24);
    return "(" + daysDifference + " days ago)";
}

$(".daysAgo").each(function () {
    var t = $(this).attr("timestamp");
    var href = $(this).attr("href");
    if (t) { 
        link = document.createElement('a');
        link.setAttribute('href', href);
        link.innerHTML = daysAgo(t);
        this.appendChild(link);
    }
});

$(".ci-app-test-result div[value=True]").addClass("success")
$(".ci-app-test-result div[value=False]").addClass("danger")
