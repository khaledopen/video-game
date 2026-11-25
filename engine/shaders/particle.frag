in vec2 v_uv; in vec4 v_col; flat in int v_kind;
out vec4 frag;
void main(){
    float r = length(v_uv), a;
    if(v_kind==0)      a = pow(max(1.-r,0.),2.2);                       // halo
    else if(v_kind==1) a = smoothstep(1.,.0,r) ;                        // fumee
    else if(v_kind==2) a = pow(max(1.-abs(v_uv.x),0.),2.)*pow(max(1.-abs(v_uv.y),0.),.8);   // etincelle
    else if(v_kind==3) a = smoothstep(1.,.86,r)*smoothstep(.62,.80,r) + .15*smoothstep(1.,.5,r); // anneau
    else { vec2 q=abs(v_uv); float star = max(0.,1.-q.x*q.y*26.-r); a = pow(max(1.-r,0.),3.)*.5 + star*star; } // eclat
    if(v_kind==1){ float al = a*v_col.a; frag = vec4(v_col.rgb*al, al); }
    else frag = vec4(v_col.rgb*a*v_col.a, 0.);
}