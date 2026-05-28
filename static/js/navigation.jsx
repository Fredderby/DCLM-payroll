(function(){
"use strict";

var userData = {};
try {
  var el = document.getElementById("nav-user-data");
  if (el) userData = JSON.parse(el.textContent);
} catch(e){}

var NAV_LINKS = [
  {section: "Main Menu", items: [
    {href: "/dashboard", icon: "fa-th-large", label: "Dashboard"},
    {href: "/staff", icon: "fa-users", label: "Staff Management"},
    {href: "/upload", icon: "fa-upload", label: "Upload Payroll"},
    {href: "/payslips", icon: "fa-file-invoice", label: "Payslips"},
    {href: "/loans", icon: "fa-hand-holding-usd", label: "Loan Management"},
    {href: "/payslips/send", icon: "fa-envelope", label: "Send Payslips"}
  ]},
  {section: "Reports", items: [
    {href: "/reports", icon: "fa-chart-bar", label: "Payroll Reports"},
    {href: "/reports/history", icon: "fa-history", label: "Upload History"}
  ]},
  {section: "Settings", items: [
    {href: "/settings/email", icon: "fa-cog", label: "Email Settings"}
  ]}
];

var curPath = window.location.pathname.replace(/\/+$/, "").toLowerCase();
var fullName = (userData.first_name || "") + " " + (userData.last_name || "");
var roleLabel = userData.role || "User";
roleLabel = roleLabel.charAt(0).toUpperCase() + roleLabel.slice(1);
var initals = ((userData.first_name && userData.first_name[0]) || "U") + ((userData.last_name && userData.last_name[0]) || "");

function isActive(href){ return href.replace(/\/+$/, "").toLowerCase() === curPath; }

/* Keep main-content margin in sync with sidebar width */
function updateMargin(collapsed){
  var w = collapsed ? "72px" : "260px";
  var mc = document.querySelector(".main-content");
  if(mc) mc.style.marginLeft = window.innerWidth < 1024 ? "70px" : w;
  var si = document.getElementById("ns-margin-style");
  if(!si){
    si = document.createElement("style");
    si.id = "ns-margin-style";
    document.head.appendChild(si);
  }
  si.textContent =
    "@media(min-width:1024px){.main-content{margin-left:" + w + "!important}}" +
    "@media(max-width:1023px){.main-content{margin-left:70px!important}}" +
    "@media(min-width:1024px){#ns-nav{width:" + w + "!important}}";
}

function init(){
  var mount = document.getElementById("navigation-mount");
  if(!mount || typeof React === "undefined" || typeof ReactDOM === "undefined") return;

  var e = React.createElement;
  var useState = React.useState;
  var useEffect = React.useEffect;

  function NavBar(){
    var c = useState(false);
    var collapsed = c[0];
    var setCollapsed = c[1];
    var m = useState(false);
    var mobOpen = m[0];
    var setMobOpen = m[1];
    var h = useState(null);
    var hover = h[0];
    var setHover = h[1];

    useEffect(function(){
      try {
        var s = localStorage.getItem("dclm_sidebar_collapsed");
        if(s === "true") { setCollapsed(true); updateMargin(true); }
        else { updateMargin(false); }
      } catch(e){ updateMargin(false); }
    }, []);

    function toggleSide(){
      setCollapsed(function(p){
        var n = !p;
        try { localStorage.setItem("dclm_sidebar_collapsed", n); } catch(e){}
        updateMargin(n);
        return n;
      });
    }

    // Prefetch on hover for faster navigation
    function prefetch(href){
      if(!href || href === window.location.pathname) return;
      var existing = document.querySelector('link[rel="prefetch"][href="' + href + '"]');
      if(existing) return;
      var link = document.createElement("link");
      link.rel = "prefetch";
      link.href = href;
      document.head.appendChild(link);
    }

    var sw = collapsed ? "72px" : "260px";

    return e("div", null,

      e("style", {dangerouslySetInnerHTML: {__html:
        "#ns-nav{transform:translateX(-100%)}" +
        "#ns-nav.open{transform:translateX(0)!important}" +
        "@media(min-width:1024px){#ns-nav{transform:translateX(0)!important}}" +
        "@media(min-width:1024px){#ns-ham{display:none!important}}"
      }}),

      // Hamburger
      e("button", {
        id: "ns-ham",
        onClick: function(){ setMobOpen(function(p){ return !p; }); },
        style: {
          position:"fixed", top:"16px", left:"16px", zIndex:60,
          width:"40px", height:"40px", display:"flex",
          alignItems:"center", justifyContent:"center",
          borderRadius:"12px", background:"rgba(0,0,0,0.4)",
          backdropFilter:"blur(8px)", border:"1px solid rgba(255,255,255,0.15)",
          cursor:"pointer", transition:"all 0.2s", padding:0
        },
        "aria-label": mobOpen ? "Close" : "Open"
      },
        e("div", {style:{display:"flex",flexDirection:"column",gap:"5px",alignItems:"center"}},
          e("span", {style:{display:"block",width:"20px",height:"2px",background:"#fff",borderRadius:"1px",transition:"all 0.3s",transform:mobOpen?"translateY(7px) rotate(45deg)":"none"}}),
          e("span", {style:{display:"block",width:"20px",height:"2px",background:"#fff",borderRadius:"1px",transition:"all 0.3s",opacity:mobOpen?0:1}}),
          e("span", {style:{display:"block",width:"20px",height:"2px",background:"#fff",borderRadius:"1px",transition:"all 0.3s",transform:mobOpen?"translateY(-7px) rotate(-45deg)":"none"}})
        )
      ),

      // Overlay
      mobOpen && e("div", {
        onClick: function(){ setMobOpen(false); },
        style:{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",zIndex:40}
      }),

      // Sidebar
      e("nav", {
        id: "ns-nav",
        className: mobOpen ? "open" : "",
        style: {
          position:"fixed", top:0, left:0, bottom:0, zIndex:50,
          display:"flex", flexDirection:"column",
          background:"rgba(15,15,35,0.88)",
          backdropFilter:"blur(24px)", WebkitBackdropFilter:"blur(24px)",
          borderRight:"1px solid rgba(255,255,255,0.08)",
          color:"#fff", transition:"all 0.3s ease", overflow:"hidden",
          width: sw
        }
      },
        // Brand
        e("div", {
          style:{
            display:"flex", alignItems:"center",
            borderBottom:"1px solid rgba(255,255,255,0.08)",
            padding: collapsed ? "20px 10px" : "24px 20px",
            justifyContent: collapsed ? "center" : "flex-start",
            gap: collapsed ? "0" : "12px"
          }
        },
          e("div", {
            style:{width:"44px",height:"44px",borderRadius:"12px",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,background:"linear-gradient(135deg,#1a365d,#2a4a7f)"}
          },
            e("img", {src:"/static/img/logo.jpg",alt:"DCLM",style:{width:"36px",height:"36px",objectFit:"contain",borderRadius:"8px"}})
          ),
          !collapsed && e("div", {style:{overflow:"hidden"}},
            e("div", {style:{fontWeight:700,fontSize:"16px",lineHeight:1.2}},"DCLM Payroll"),
            e("div", {style:{fontSize:"11px",opacity:0.6}},"Management System")
          )
        ),

        // Menu
        e("div", {
          style:{
            flex:1, overflowY:"auto", overflowX:"hidden",
            padding: collapsed ? "16px 8px" : "16px 12px"
          }
        },
          NAV_LINKS.map(function(g, gi){
            return e("div", {key: gi},
              !collapsed && e("div", {
                style:{
                  fontSize:"10px", textTransform:"uppercase", letterSpacing:"1px",
                  opacity:0.4, fontWeight:600, padding:"0 12px 8px",
                  marginTop: gi > 0 ? "24px" : 0
                }
              }, g.section),
              g.items.map(function(link){
                var active = isActive(link.href);
                var isHov = hover === link.href;
                return e("a", {
                  key: link.href,
                  href: link.href,
                  title: collapsed ? link.label : undefined,
                  onMouseEnter: function(){ setHover(link.href); prefetch(link.href); },
                  onMouseLeave: function(){ setHover(null); },
                  style: {
                    display:"flex", alignItems:"center",
                    borderRadius:"10px", fontSize:"14px", fontWeight:active?700:500,
                    textDecoration:"none", marginBottom:"2px", transition:"all 0.2s",
                    cursor:"pointer", position:"relative",
                    color: active ? "#fff" : "rgba(255,255,255,0.65)",
                    background: active ? "linear-gradient(135deg,#1a365d,#2a4a7f)" : (isHov ? "rgba(255,255,255,0.08)" : "transparent"),
                    boxShadow: active ? "0 8px 20px rgba(26,54,93,0.22)" : "none",
                    padding: collapsed ? "12px" : "10px 12px",
                    justifyContent: collapsed ? "center" : "flex-start",
                    gap: collapsed ? 0 : "12px"
                  }
                },
                  e("i", {className:"fas "+link.icon,style:{width:"20px",textAlign:"center",fontSize:"14px"}}),
                  !collapsed && e("span", {style:{whiteSpace:"nowrap"}}, link.label),
                  collapsed && active && e("span", {
                    style:{position:"absolute",right:"4px",top:"50%",transform:"translateY(-50%)",width:"5px",height:"5px",borderRadius:"50%",background:"#60a5fa"}
                  })
                );
              })
            );
          })
        ),

        // Footer
        e("div", {
          style:{
            borderTop:"1px solid rgba(255,255,255,0.08)",
            padding: collapsed ? "12px 8px" : "16px 16px"
          }
        },
          e("div", {
            style:{
              display:"flex", alignItems:"center", gap:"12px",
              justifyContent: collapsed ? "center" : "flex-start"
            }
          },
            e("div", {
              style:{
                width:"36px",height:"36px",borderRadius:"10px",
                display:"flex",alignItems:"center",justifyContent:"center",
                fontSize:"14px",fontWeight:700,flexShrink:0,
                background:"linear-gradient(135deg,#1a365d,#0f3460)"
              }
            }, initals),
            !collapsed && e("div", {style:{flex:1,minWidth:0,overflow:"hidden"}},
              e("div", {style:{fontSize:"13px",fontWeight:600,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}, fullName),
              e("div", {style:{fontSize:"11px",opacity:0.5,display:"flex",alignItems:"center",gap:"4px"}},
                e("i", {className:"fas fa-circle",style:{fontSize:"6px",color:"#10b981"}}),
                roleLabel
              )
            ),
            e("button", {
              onClick: toggleSide,
              style:{
                background:"none",border:"none",color:"rgba(255,255,255,0.4)",
                cursor:"pointer",padding:"6px",borderRadius:"8px",fontSize:"11px",
                display:"none"
              },
              className: "lg-inline"
            },
              e("i", {className:"fas " + (collapsed ? "fa-chevron-right" : "fa-chevron-left")})
            ),
            e("a", {
              href: "/logout",
              style:{
                color:"rgba(255,255,255,0.4)",textDecoration:"none",
                padding:"6px",borderRadius:"8px",fontSize:"11px",cursor:"pointer"
              },
              title:"Logout"
            },
              e("i", {className:"fas fa-sign-out-alt"})
            )
          )
        )
      )
    );
  }

  var root = ReactDOM.createRoot(mount);
  root.render(e(NavBar));
}

if(document.readyState === "complete" || document.readyState === "interactive"){
  setTimeout(init, 0);
} else {
  document.addEventListener("DOMContentLoaded", function(){ setTimeout(init, 0); });
}

})();
