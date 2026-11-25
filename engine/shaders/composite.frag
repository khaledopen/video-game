#version 330 core
uniform sampler2D u_scene, u_bloom;
uniform vec2 u_texel; uniform float u_time, u_bloomK, u_speed, u_aberr, u_vig, u_flash, u_desat, u_fade, u_grain, u_drops, u_glitch, u_fx;
uniform vec3 u_flashCol, u_tint; uniform vec2 u_center;
in vec2 uv; out vec4 frag;
float h21(vec2 p){ vec3 q = fract(vec3(p.xyx)*.1031); q += dot(q,q.yzx+33.33); return fract((q.x+q.y)*q.z); }
vec3 aces(vec3 x){ return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.); }
float luma(vec3 c){ return dot(c/(1.+c), vec3(.299,.587,.114)); }
vec3 fxaa(vec2 p){
    vec3 m = texture(u_scene,p).rgb;
    float lm = luma(m);
    float nw=luma(texture(u_scene,p+u_texel*vec2(-1,-1)).rgb), ne=luma(texture(u_scene,p+u_texel*vec2(1,-1)).rgb);
    float sw=luma(texture(u_scene,p+u_texel*vec2(-1,1)).rgb), se=luma(texture(u_scene,p+u_texel*vec2(1,1)).rgb);
    float mn=min(lm,min(min(nw,ne),min(sw,se))), mx=max(lm,max(max(nw,ne),max(sw,se)));
    if(mx-mn < max(.03, mx*.12)) return m;
    vec2 d = vec2(-((nw+ne)-(sw+se)), (nw+sw)-(ne+se));
    float rd = max((nw+ne+sw+se)*.03125, .0078);
    d = clamp(d/(min(abs(d.x),abs(d.y))+rd), -6., 6.)*u_texel;
    vec3 a = .5*(texture(u_scene,p+d*(1./3.-.5)).rgb+texture(u_scene,p+d*(2./3.-.5)).rgb);
    vec3 b = a*.5+.25*(texture(u_scene,p-d*.5).rgb+texture(u_scene,p+d*.5).rgb);
    float lb = luma(b);
    return (lb<mn||lb>mx) ? a : b;
}
void main(){
    vec2 p = uv;
    if(u_glitch>0.){ float ln = floor(p.y*42.); float g = step(1.-u_glitch*.45, h21(vec2(ln, floor(u_time*26.)))); p.x += (h21(vec2(ln,u_time))-.5)*.07*g*u_glitch; }
    if(u_drops>0.){                                  // gouttes sur l'objectif
        for(int k=0;k<2;k++){
            float sc = 7.+6.*float(k);
            vec2 g = p*vec2(sc*1.78,sc); g.y += u_time*(.10+.07*float(k));
            vec2 id = floor(g), f = fract(g)-.5;
            float h = h21(id+float(k)*31.);
            vec2 o = vec2(h-.5, fract(h*17.)-.5)*.6;
            float life = fract(u_time*.22+h*7.);
            float r = (.05+.13*fract(h*31.))*smoothstep(0.,.15,life)*(1.-life);
            float dd = length((f-o)*vec2(1.,.8));
            if(h>.62 && dd<r){ p -= (f-o)*.10*(1.-dd/r)*u_drops; }
        }
    }
    vec2 d = p - u_center;
    vec3 c;
    float k = u_speed * smoothstep(.10,.75,length(d*vec2(1.2,1.)));
    if(k > .004){
        c = vec3(0.); float j = h21(gl_FragCoord.xy)*.5;
        for(int i=0;i<7;i++){ float f = 1. - k*.11*(float(i)+j)/7.; c += texture(u_scene, u_center+d*f).rgb; }
        c /= 7.;
    } else c = u_fx>.5 ? fxaa(p) : texture(u_scene,p).rgb;
    if(u_aberr>.0003 && k<=.004){ vec2 o = d*u_aberr*length(d); c.r = texture(u_scene,p+o).r; c.b = texture(u_scene,p-o).b; }
    c += texture(u_bloom, p).rgb * u_bloomK;
    c *= 1.08;
    c = aces(c);
    c = pow(c, vec3(1./2.2));
    c = mix(c, c*c*(3.-2.*c), .22);
    c *= u_tint;
    float g = dot(c, vec3(.3,.59,.11)); c = mix(c, vec3(g), u_desat);
    vec2 q = uv-.5; c *= 1. - u_vig*smoothstep(.25,1.05,length(q*vec2(1.15,1.)));
    c += (h21(gl_FragCoord.xy+fract(u_time)*91.)-.5)*u_grain;
    c = mix(c, u_flashCol, clamp(u_flash,0.,1.));
    frag = vec4(c*u_fade,1.);
}