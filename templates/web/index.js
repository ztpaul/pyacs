window.onload=function()
{ 
    document.getElementById('selectMethod').onchange(this.value);
}

function OnSubmit()
{
    window.history.replaceState(null, null, window.location.href);
    return true
}



function OnChangeMethod(value)
{
    if(value=="SetParameterValues")
    {
        document.getElementById('tdValue').style.display = "";
        document.getElementById('tdInputValue').style.display = "";
    }
    else
    {
        document.getElementById('tdValue').style.display = "none";
        document.getElementById('tdInputValue').style.display = "none";
    }
    //alert(value)
}
 