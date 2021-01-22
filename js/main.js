
const handleTabs = function() {
    document.querySelectorAll('.tab-button').forEach(function(tab) {
        tab.addEventListener('click', tabClick);
    });
}

const tabClick = function() {
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.style.display = 'none';
    });
    document.getElementById(this.id + '-div').style.display = '';
}

document.addEventListener('DOMContentLoaded', function() {
    handleTabs();
});