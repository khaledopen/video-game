#version 330 core
uniform vec2 u_size;
in vec2 in_pos;
in vec4 i_rect;      // x, y, w, h (pixels)
in vec4 i_uv;        // u0, v0, u1, v1
in vec4 i_c0; in vec4 i_c1; in vec4 i_c2;
in vec4 i_par;       // selon le type
in vec4 i_par2;      // type, inclinaison, rotation, option
out vec2 v_p; out vec2 v_half; out vec2 v_uv; out vec2 v_t;
flat out vec4 v_c0; flat out vec4 v_c1; flat out vec4 v_c2; flat out vec4 v_par; flat out int v_kind; flat out vec4 v_par2;
void main(){
    int k = int(i_par2.x+.5);
    vec2 half_s = i_rect.zw*.5;
    float pad = (k==0 || k==5) ? i_par.z + 2. : (k==1 || k==2) ? 0. : 1.;
    vec2 q = in_pos*(half_s + pad);
    v_p = q; v_half = half_s;
    v_t = q/(2.*half_s)+.5;
    v_uv = mix(i_uv.xy, i_uv.zw, v_t);
    q.x -= q.y * i_par2.y;
    float c = cos(i_par2.z), s = sin(i_par2.z);
    q = vec2(c*q.x - s*q.y, s*q.x + c*q.y);
    vec2 w = i_rect.xy + half_s + q;
    v_c0=i_c0; v_c1=i_c1; v_c2=i_c2; v_par=i_par; v_par2=i_par2; v_kind=k;
    gl_Position = vec4(w.x/u_size.x*2.-1., 1.-w.y/u_size.y*2., 0., 1.);
}