uniform sampler2D u_bend;
in vec3 in_pos; in vec3 in_norm; in vec2 in_uv; in float in_mat;
in vec3 i_pos; in vec3 i_rot; in vec3 i_scale; in vec3 i_c1; in vec3 i_c2; in vec4 i_par;
out vec3 v_pos; out vec3 v_norm; out vec2 v_uv; out vec3 v_obj; out vec3 v_c1; out vec3 v_c2; out vec4 v_par;
flat out int v_mat; flat out vec3 v_seed;
void main(){
    vec3 p = in_pos * i_scale, n = in_norm / i_scale;
    v_obj = p;
    float c,s;
    c=cos(i_rot.z); s=sin(i_rot.z); p.xy = mat2(c,s,-s,c)*p.xy; n.xy = mat2(c,s,-s,c)*n.xy;
    c=cos(i_rot.y); s=sin(i_rot.y); p.yz = mat2(c,s,-s,c)*p.yz; n.yz = mat2(c,s,-s,c)*n.yz;
    c=cos(i_rot.x); s=sin(i_rot.x); p.xz = mat2(c,-s,s,c)*p.xz; n.xz = mat2(c,-s,s,c)*n.xz;
    vec3 w = p + i_pos;
    v_pos = w; v_norm = n; v_uv = in_uv; v_c1 = i_c1; v_c2 = i_c2; v_par = i_par;
    v_mat = int(in_mat + .5); v_seed = vec3(i_par.w, i_scale.y, i_pos.x);
    vec2 b = texture(u_bend, vec2((w.z + 30.) / u_track.z, .5)).xy;
    vec3 q = w; q.y *= u_track.w;
    q.xy += b;
    gl_Position = u_vp * vec4(q, 1.);
    gl_ClipDistance[0] = u_track.w < 0. ? w.y - .015 : 1.;
}
