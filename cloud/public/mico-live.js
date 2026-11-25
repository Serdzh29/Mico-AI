/* Mico AI: живой Mico для сайта. Порт отрисовки из приложения (ui/blob.py): форма-«камушек» с плывущими гармониками,
   дыхание, покачивание головы, моргание, взгляд за курсором, дрейф лица, независимые брови, радость, растерянность и прыжок. */
(function(){
var TAU=Math.PI*2,N=96,HEAD_MAX=7;
var TILT={curious:7,sad:-4,worried:-3,thinking:4,proud:-6,playful:5,confused:6};
function clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function rnd(a,b){return a+Math.random()*(b-a)}
function mix(a,b,k){return [a[0]*(1-k)+b[0]*k,a[1]*(1-k)+b[1]*k,a[2]*(1-k)+b[2]*k]}
function rgba(c,a){return "rgba("+(c[0]|0)+","+(c[1]|0)+","+(c[2]|0)+","+a+")"}
function hex(h){h=h.replace("#","");return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]}
function pulse(x,a,b){return (x<=a||x>=b)?0:Math.sin(Math.PI*(x-a)/(b-a))}
function easeOutBack(x){x=clamp(x,0,1);var c1=1.70158,c3=2.70158;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2)}
function pebble(a,wob,t,k){
 var r=1+(0.085+0.025*k*Math.sin(t*0.35))*Math.sin(2*a+0.9+0.55*k*Math.sin(t*0.23))
  +(0.055+0.02*k*Math.sin(t*0.41+1))*Math.sin(3*a+2.1+0.6*k*Math.sin(t*0.31+2))
  +0.025*Math.sin(5*a+0.3*k*Math.sin(t*0.5));
 return r+wob*(0.012*Math.sin(3*a+t*2)+0.01*Math.sin(4*a-t*1.6));
}
/* Дуга по правилам Qt: углы против часовой стрелки от «3 часов», ось y вниз */
function arcQt(c,cx,cy,rx,ry,start,span){
 var s=start*Math.PI/180,e=(start+span)*Math.PI/180;
 c.ellipse(cx,cy,Math.abs(rx),Math.abs(ry),0,-s,-e,true);
}
function Mico(canvas,opt){
 opt=opt||{};
 this.cv=canvas;this.c=canvas.getContext("2d");
 this.col=hex(opt.color||"#FFCFA3");
 this.baseMood=opt.mood||"idle";this.mood=this.baseMood;this.moodUntil=0;
 this.t0=performance.now()/1000;this.last=this.t0;
 this.anim=null;this.nextIdle=this.t0+4;
 this.blinkAt=this.t0+2.5;this.blinkStart=0;this.blinkUntil=0;this.lid=1;
 this.jh=0;this.jv=0;this.squash=0;this.squashV=0;this.tilt=0;
 this.brow={l:0,r:0,tl:0,tr:0,gl:0,gr:0,gtl:0,gtr:0,until:0};
 this.face={dx:0,dy:0,gx:0,gy:0,until:0};
 this.px=null;this.py=null;this.tiltDir=1;
 this.appear=opt.appear!==false?{start:this.t0,dur:0.9}:null;
 this.running=false;this.visible=true;this.size=0;this.dpr=1;
 var self=this;
 this.onMove=function(e){self.px=e.clientX;self.py=e.clientY};
 this.onTouch=function(e){var t=e.touches&&e.touches[0];if(t){self.px=t.clientX;self.py=t.clientY}};
 addEventListener("pointermove",this.onMove,{passive:true});addEventListener("touchmove",this.onTouch,{passive:true});
 this.resize();addEventListener("resize",function(){self.resize()});
 if("IntersectionObserver" in window){new IntersectionObserver(function(es){self.visible=es[0].isIntersecting;if(self.visible&&!self.running)self.start()}).observe(canvas)}
 this.start();
}
Mico.prototype.resize=function(){
 var r=this.cv.getBoundingClientRect(),d=Math.min(2,window.devicePixelRatio||1),s=Math.max(60,Math.round(r.width));
 this.size=s;this.dpr=d;this.cv.width=Math.round(s*d);this.cv.height=Math.round(s*d);
};
Mico.prototype.start=function(){
 if(this.running)return;this.running=true;var self=this;
 (function loop(){
  if(!self.visible||document.hidden){self.running=false;return}
  self.frame(performance.now()/1000);requestAnimationFrame(loop)})();
};
Mico.prototype.setMood=function(m,secs){this.mood=m;this.moodUntil=secs?performance.now()/1000+secs:0};
Mico.prototype.jump=function(p){this.jv=p||280};
Mico.prototype.startAnim=function(n){
 var dur={lookaround:2.6,blink2:0.6,wink:0.9,headtilt:1.8}[n]||1;
 if(n==="headtilt")this.tiltDir=Math.random()<.5?-1:1;
 this.anim={name:n,start:performance.now()/1000,dur:dur};
};
Mico.prototype.animU=function(now){return this.anim?Math.min(1,(now-this.anim.start)/this.anim.dur):null};
Mico.prototype.tick=function(now,dt){
 if(this.moodUntil&&now>this.moodUntil){this.mood=this.baseMood;this.moodUntil=0}
 if(now>this.blinkAt){this.blinkStart=now;this.blinkUntil=now+0.2;this.blinkAt=now+rnd(3,6)}
 var close=now<this.blinkUntil?pulse((now-this.blinkStart)/0.2,0,1):0;
 if(this.anim&&this.anim.name==="blink2"){var u=Math.min(1,(now-this.anim.start)/this.anim.dur);close=Math.max(close,Math.max(pulse(u,0,.3),pulse(u,.4,.7)))}
 this.lid=1-0.92*close;
 if(this.anim&&now>this.anim.start+this.anim.dur)this.anim=null;
 if(!this.anim&&this.mood==="idle"&&now>this.nextIdle){
  var a=["lookaround","blink2","wink","headtilt"];this.startAnim(a[(Math.random()*a.length)|0]);this.nextIdle=now+rnd(8,16)}
 if(this.jh>0||this.jv!==0){this.jv-=900*dt;this.jh+=this.jv*dt;
  if(this.jh<=0&&this.jv<0){if(this.jv<-120)this.squashV+=0.6;this.jh=this.jv=0}}
 var mood=this.eMood();
 var goal=(TILT[mood]||0);this.tilt+=(clamp(goal,-HEAD_MAX,HEAD_MAX)-this.tilt)*(1-Math.exp(-dt*7));
 var ex=function(r){return 1-Math.exp(-dt*r)};
 var b=this.brow;
 if(now>=b.until){var amp=0.35;b.gl=rnd(-0.03,0.055)*amp;b.gr=rnd(-0.03,0.055)*amp;b.gtl=rnd(-0.03,0.03)*amp;b.gtr=rnd(-0.03,0.03)*amp;b.until=now+rnd(2,5)}
 var kb=ex(9);b.l+=(b.gl-b.l)*kb;b.r+=(b.gr-b.r)*kb;b.tl+=(b.gtl-b.tl)*kb;b.tr+=(b.gtr-b.tr)*kb;
 var f=this.face;
 if(now>=f.until){var g=0.05;f.gx=rnd(-g,g);f.gy=rnd(-g*0.8,g*0.6);f.until=now+rnd(1.2,3)}
 var kf=ex(2.2);f.dx+=(f.gx-f.dx)*kf;f.dy+=(f.gy-f.dy)*kf;
 this.squashV+=(-60*this.squash-8*this.squashV)*dt;this.squash+=this.squashV*dt;
};
Mico.prototype.eMood=function(){return this.mood};
Mico.prototype.look=function(fxs,fys,R,mood,u,anim,now){
 var vx=0,vy=0;
 if(anim==="headtilt"&&u!==null){vx=-this.tiltDir*R*0.05*Math.sin(Math.PI*u);vy=-R*0.01}
 else if(mood==="thinking"){vx=R*0.04*Math.sin(now*2);vy=-R*0.05}
 else if(anim==="lookaround"&&u!==null){vx=Math.sin(u*TAU*1.5)*R*0.05}
 else if(mood==="curious"){vx=R*0.03;vy=-R*0.01}
 else if(this.px!==null){
  var r=this.cv.getBoundingClientRect(),sc=r.width/this.size;
  var dx=(this.px-(r.left+fxs*sc)),dy=(this.py-(r.top+fys*sc));
  var d=Math.hypot(dx,dy)||1,k=Math.min(d/200,1)*R*0.045/d;vx=dx*k;vy=dy*k;
 }
 vx+=(Math.sin(now*1.3)+0.5*Math.sin(now*3.1+1))*R*0.006;vy+=(Math.cos(now*1.7)+0.5*Math.sin(now*2.7))*R*0.005;
 return [vx,vy];
};
Mico.prototype.frame=function(now){
 var dt=Math.min(0.05,Math.max(0.001,now-this.last));this.last=now;this.tick(now,dt);this.draw(now);
};
Mico.prototype.draw=function(now){
 var c=this.c,S=this.size,sc=S/300,t=now-this.t0;
 c.setTransform(this.dpr,0,0,this.dpr,0,0);c.clearRect(0,0,S,S);
 var w=S,cx=w/2,R=w*0.28,cy0=S*0.54,cy=cy0-this.jh*sc;
 var mood=this.eMood(),u=this.animU(now),anim=this.anim?this.anim.name:null;
 if(anim==="wink")mood="curious";
 var speed=mood==="sleepy"?0.6:1,breath=1+0.03*Math.sin(t*1.6*speed);
 var sx=breath*(1+this.squash),sy=breath*(1-this.squash);
 cy-=R*0.025*Math.sin(t*1.9);
 var baseOp=1;
 if(this.appear){var au=(now-this.appear.start)/this.appear.dur;
  if(au>=1)this.appear=null;else{var pop=Math.max(0.05,easeOutBack(Math.min(1,au/0.8)));sx*=pop;sy*=pop;baseOp=Math.min(1,au*2.4)}}
 if(mood==="proud"){sx*=0.97;sy*=1.05}
 var wob=mood==="thinking"?2.5:1;
 var shake=mood==="laugh"?Math.sin(t*28)*3:mood==="scared"?Math.sin(t*40)*1.2:0;
 var sway=Math.sin(t*0.7)*1.8;
 if(anim==="headtilt"&&u!==null){sway+=this.tiltDir*6*Math.sin(Math.PI*u);mood="curious"}
 var col=this.col;
 c.globalAlpha=baseOp;
 /* тень */
 c.fillStyle=rgba([120,70,40],Math.max(8,34-this.jh*0.4*sc)/255);
 c.beginPath();c.ellipse(cx,cy0+R*1.18,R*0.85*sx*(1-this.jh/300),R*0.13,0,0,TAU);c.fill();
 c.save();c.translate(cx,cy);
 var head=clamp(this.tilt+sway,-HEAD_MAX,HEAD_MAX);c.rotate((head+shake)*Math.PI/180);c.translate(-cx,-cy);
 /* форма */
 c.beginPath();
 for(var i=0;i<N;i++){var a=TAU*i/N,r=pebble(a,wob,t,0.5),bx=Math.cos(a)*r*1.05,by=Math.sin(a)*r*0.98,x=cx+bx*R*sx,y=cy+by*R*sy;
  if(i===0)c.moveTo(x,y);else c.lineTo(x,y)}
 c.closePath();
 var body=col,glow=mix(body,[255,255,255],0.55);
 c.lineJoin="round";
 [[0.34,12],[0.20,20],[0.10,28]].forEach(function(p){c.strokeStyle=rgba(glow,p[1]/255);c.lineWidth=R*p[0];c.stroke()});
 var pink=[255,160,150];
 var g=c.createRadialGradient(cx-R*0.15,cy-R*0.2,0,cx-R*0.15,cy-R*0.2,R*1.3);
 g.addColorStop(0,rgba(mix(body,[255,250,240],0.35),1));g.addColorStop(0.55,rgba(body,1));
 g.addColorStop(0.85,rgba(mix(body,pink,0.35),1));g.addColorStop(1,rgba(mix(body,pink,0.6),1));
 c.fillStyle=g;c.fill();
 c.save();c.clip();
 var sh=c.createRadialGradient(cx-R*0.45,cy-R*0.6,0,cx-R*0.45,cy-R*0.6,R*0.6);
 sh.addColorStop(0,"rgba(255,255,255,"+(130/255)+")");sh.addColorStop(1,"rgba(255,255,255,0)");c.fillStyle=sh;c.fillRect(0,0,S,S);
 var ir=c.createRadialGradient(cx+R*0.85,cy+R*0.6,0,cx+R*0.85,cy+R*0.6,R*0.65);
 ir.addColorStop(0,"rgba(170,240,220,"+(80/255)+")");ir.addColorStop(1,"rgba(170,240,220,0)");c.fillStyle=ir;c.fillRect(0,0,S,S);
 c.restore();
 /* светящийся край: обводка внутри формы */
 c.save();c.clip();c.strokeStyle="rgba(255,255,255,"+(95/255)+")";c.lineWidth=R*0.08;c.stroke();c.restore();
 /* лицо */
 var fx=cx-R*0.12+R*this.face.dx,fy=cy-R*0.16+R*this.face.dy;
 this.drawFace(c,fx,fy,R,col,mood,t,u,anim,now);
 c.restore();c.globalAlpha=1;
};
Mico.prototype.drawFace=function(c,fx,fy,R,col,mood,t,u,anim,now){
 var dark=((Math.max(col[0],col[1],col[2])+Math.min(col[0],col[1],col[2]))/2)>110;
 var ink=dark?"#2a1d1d":"#ffffff",shine=dark?"rgb(255,255,255)":"rgb(40,30,20)";
 var look=this.look(fx,fy,R,mood,u,anim,now),lw=Math.max(1.6,R*0.03);
 c.lineCap="round";c.lineJoin="round";
 /* румянец */
 c.fillStyle=rgba([255,120,120],((mood==="shy"||mood==="proud")?160:(["happy","love","laugh","excited"].indexOf(mood)>=0)?105:55)/255);
 [-1,1].forEach(function(s){c.beginPath();c.ellipse(fx+s*R*0.52,fy+R*0.22,R*0.12,R*0.075,0,0,TAU);c.fill()});
 var self=this,eyeK=1;
 [-1,1].forEach(function(s){
  var ex=fx+s*R*0.38+look[0],ey=fy+look[1]+(mood==="shy"?R*0.05:0)-(mood==="confused"&&s===1?R*0.02:0);
  var ew=R*0.075,eh=R*0.105,squint=mood==="curious"&&s===-1;
  c.strokeStyle=ink;c.lineWidth=lw;c.fillStyle=ink;
  if(mood==="sleepy"||(mood==="playful"&&s===1)){c.beginPath();c.moveTo(ex-ew,ey);c.lineTo(ex+ew,ey);c.stroke()}
  else if(["happy","laugh","love","proud","playful"].indexOf(mood)>=0){c.beginPath();arcQt(c,ex,ey-eh*0.5+eh*0.75,ew*1.15,eh*0.75,0,180);c.stroke()}
  else if(squint){c.beginPath();c.ellipse(ex,ey+eh*0.2,ew*1.05,eh*0.4,0,0,TAU);c.fill()}
  else{
   var big=(mood==="surprised"?1.35:mood==="scared"?1.3:mood==="excited"?1.15:1)*eyeK,sq=mood==="angry"?0.75:1,lid=self.lid;
   c.beginPath();c.ellipse(ex,ey,ew*big,eh*big*sq*lid,0,0,TAU);c.fill();
   c.fillStyle=shine;c.beginPath();c.ellipse(ex+ew*0.3,ey-eh*0.3*sq*lid,ew*0.32*big,ew*0.32*big*lid,0,0,TAU);c.fill();
  }
  /* брови */
  var by=ey-R*0.2-look[1]*0.5,so=R*0.01,si=-R*0.005,curve=R*0.045;
  if(mood==="sad"){so=R*0.03;si=-R*0.05;curve=R*0.012}
  else if(mood==="worried"){so=R*0.04;si=-R*0.07;curve=R*0.01}
  else if(mood==="surprised"||mood==="scared"||mood==="excited"){by-=R*(mood==="surprised"||mood==="excited"?0.05:0.07);curve=R*0.06}
  else if(mood==="angry"){so=-R*0.02;si=R*0.05;curve=R*0.01}
  else if(mood==="shy"){by+=R*0.02;curve=R*0.02}
  else if(mood==="confused"&&s===1){by-=R*0.07}
  else if(mood==="thinking"||mood==="curious"){if(s===1)by-=R*0.06;else if(squint){by+=R*0.03;curve=R*0.01}}
  var bo=self.brow;by-=R*(s===-1?bo.l:bo.r);var bt=s===-1?bo.tl:bo.tr;so+=R*bt;si-=R*bt;
  var bl=R*0.09;c.strokeStyle=ink;c.lineWidth=Math.max(1.4,R*0.024);
  c.beginPath();c.moveTo(ex+s*bl,by+so);c.quadraticCurveTo(ex,by-curve,ex-s*bl,by+si);c.stroke();
 });
 /* рот */
 c.strokeStyle=ink;c.lineWidth=lw;c.fillStyle=ink;
 var my=fy+R*0.22;
 if(["happy","love","proud","playful"].indexOf(mood)>=0){c.beginPath();arcQt(c,fx,my-R*0.07+R*0.10,R*0.17,R*0.10,200,140);c.stroke()}
 else if(mood==="laugh"||mood==="excited"){var bg=mood==="laugh"?1+0.2*Math.sin(t*18):1,rw=mood==="laugh"?R*0.13:R*0.14,rh=mood==="laugh"?R*0.2:R*0.2;
  c.beginPath();c.ellipse(fx,my-R*0.03+rh*bg/2,rw*bg,rh*bg/2,0,0,Math.PI,false);c.closePath();c.fill()}
 else if(mood==="sad"){c.beginPath();c.moveTo(fx-R*0.14,my+R*0.1);c.quadraticCurveTo(fx,my-R*0.06,fx+R*0.14,my+R*0.1);c.lineWidth=Math.max(1.2,R*0.03);c.stroke()}
 else if(mood==="worried"){c.beginPath();c.ellipse(fx,my+R*0.05,R*0.03,R*0.04,0,0,TAU);c.fill()}
 else if(mood==="angry"){c.beginPath();c.moveTo(fx-R*0.1,my+R*0.02);c.quadraticCurveTo(fx,my+R*0.1,fx+R*0.1,my+R*0.02);c.stroke()}
 else if(mood==="shy"){c.beginPath();arcQt(c,fx,my-R*0.02+R*0.04,R*0.06,R*0.04,200,140);c.stroke()}
 else if(mood==="confused"){c.beginPath();for(var i=0;i<9;i++){var x2=fx-R*0.1+i*R*0.025,y2=my+R*0.04+Math.sin(i*1.4)*R*0.012;if(i===0)c.moveTo(x2,y2);else c.lineTo(x2,y2)}c.stroke()}
 else if(mood==="surprised"){c.beginPath();c.ellipse(fx,my+R*0.05,R*0.04,R*0.058,0,0,TAU);c.fill()}
 else if(mood==="curious"||mood==="thinking"){c.beginPath();c.moveTo(fx-R*0.05,my+R*0.05);c.lineTo(fx+R*0.09,my+R*0.03);c.stroke()}
 else if(mood==="sleepy"){var rr=R*(0.03+0.012*Math.sin(t*1.2));c.beginPath();c.ellipse(fx,my+R*0.05,rr,rr*1.2,0,0,TAU);c.stroke()}
 else{c.beginPath();arcQt(c,fx,my-R*0.04+R*0.06,R*0.1,R*0.06,210,120);c.stroke()}
};
window.MicoLive={create:function(cv,o){return new Mico(cv,o)},_Mico:Mico};
})();
