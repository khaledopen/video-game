#version 330 core
uniform sampler2D u_tex; uniform vec2 u_texel; uniform float u_thr;
in vec2 uv; out vec4 frag;
vec3 pick(vec3 c){ if(u_thr<=0.) return c; float l = max(c.r,max(c.g,c.b)); float k = max(l-u_thr,0.)/max(l,1e-4); return min(c*k, vec3(12.)); }
void main(){
    vec3 a = texture(u_tex, uv).rgb*4.;
    a += texture(u_tex, uv+u_texel*vec2(-1,-1)).rgb; a += texture(u_tex, uv+u_texel*vec2(1,-1)).rgb;
    a += texture(u_tex, uv+u_texel*vec2(-1,1)).rgb;  a += texture(u_tex, uv+u_texel*vec2(1,1)).rgb;
    frag = vec4(pick(a/8.),1.);
}