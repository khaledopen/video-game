in vec2 v_uv; in float v_a; in vec3 v_c; out vec4 frag;
void main(){ float a = (1.-v_uv.x*v_uv.x)*(1.-v_uv.y*v_uv.y); frag = vec4(v_c*a*v_a, 0.); }